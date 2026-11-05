import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import ANY, patch
from types import SimpleNamespace

from backend.app import main
from backend.app import intent_parser
from backend.app.gemini_understanding import GeminiUnderstandingError


class ProcessAudioRouteTests(unittest.TestCase):
    def setUp(self):
        self.previous_testing = main.app.config.get("TESTING", False)
        main.app.config["TESTING"] = True
        self.database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database_path = self.database_file.name
        self.database_file.close()
        connection = sqlite3.connect(self.database_path)
        try:
            connection.executescript(
                """
                CREATE TABLE Inventory (
                    ItemID INTEGER PRIMARY KEY,
                    ItemName TEXT,
                    ItemNameHindi TEXT,
                    IsActive INTEGER DEFAULT 1
                );
                CREATE TABLE CustomerCredit (
                    CustomerID INTEGER PRIMARY KEY,
                    CustomerName TEXT,
                    CustomerNameHindi TEXT,
                    IsActive INTEGER DEFAULT 1
                );
                """
            )
        finally:
            connection.close()
        self.database_patch = patch.object(intent_parser, "DB_PATH", self.database_path)
        self.database_patch.start()

    def tearDown(self):
        self.database_patch.stop()
        main.app.config["TESTING"] = self.previous_testing
        if os.path.exists(self.database_path):
            os.remove(self.database_path)

    def test_postgres_voice_sale_uses_store_inventory_for_confirmation(self):
        from backend.app.models import StoreCredit, StoreInventory

        with (
            main.app.app_context(),
            patch.dict(
                os.environ,
                {"GNANI_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"},
            ),
            patch("backend.app.main.is_postgres_database", return_value=True),
            patch("backend.app.main.current_store_id", return_value=7),
            patch("backend.app.main.transcribe_audio", return_value="५० मैगी बेच दो"),
            patch("backend.app.main.understand_command") as understand_command,
            patch("backend.app.main.parse_and_execute") as parse_and_execute,
            patch("backend.app.models.StoreInventory.query") as inventory_query,
            patch("backend.app.models.StoreCredit.query") as customer_query,
            patch(
                "backend.app.gemini_understanding.resolve_catalog_entity",
                return_value=None,
            ),
        ):
            understand_command.return_value = {
                "action": "sell",
                "entity": "Maggi",
                "quantity": "50",
            }
            inventory_query.filter_by.return_value.order_by.return_value.all.return_value = [
                SimpleNamespace(
                    item_id=3,
                    item_name="मैगी (MRP ₹14)",
                    item_name_hindi=None,
                    stock_quantity=100,
                    price=14,
                )
            ]
            customer_query.filter_by.return_value.order_by.return_value.all.return_value = []

            response = main.app.test_client().post(
                "/api/process-audio",
                data={
                    "audio": (io.BytesIO(b"audio"), "command.wav"),
                    "lang": "hi-IN",
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        database_action = response.get_json()["database_action"]
        self.assertEqual(database_action["status"], "pending_selection")
        self.assertEqual(database_action["draft"]["Quantity"], 50)
        self.assertEqual(
            [item["ItemName"] for item in database_action["draft"]["Candidates"]],
            ["मैगी (MRP ₹14)"],
        )
        self.assertEqual(
            understand_command.call_args.kwargs["inventory"],
            ["मैगी (MRP ₹14)"],
        )
        parse_and_execute.assert_not_called()

    def test_postgres_voice_credit_uses_store_customer_and_requires_confirmation(self):
        from backend.app.models import StoreCredit, StoreInventory

        with (
            main.app.app_context(),
            patch.dict(
                os.environ,
                {"GNANI_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"},
            ),
            patch("backend.app.main.is_postgres_database", return_value=True),
            patch("backend.app.main.current_store_id", return_value=7),
            patch(
                "backend.app.main.transcribe_audio",
                return_value="रमेश के खाते में २,५०० डाल दो",
            ),
            patch("backend.app.main.understand_command") as understand_command,
            patch("backend.app.main.parse_and_execute") as parse_and_execute,
            patch("backend.app.models.StoreInventory.query") as inventory_query,
            patch("backend.app.models.StoreCredit.query") as customer_query,
        ):
            understand_command.return_value = {
                "action": "credit",
                "entity": "रमेश",
                "quantity": "2",
            }
            inventory_query.filter_by.return_value.order_by.return_value.all.return_value = []
            customer_query.filter_by.return_value.order_by.return_value.all.return_value = [
                SimpleNamespace(
                    customer_id=4,
                    customer_name="Ramesh",
                    customer_name_hindi="रमेश",
                    outstanding_balance=250,
                )
            ]

            response = main.app.test_client().post(
                "/api/process-audio",
                data={
                    "audio": (io.BytesIO(b"audio"), "command.wav"),
                    "lang": "hi-IN",
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        database_action = response.get_json()["database_action"]
        self.assertEqual(database_action["status"], "pending_confirmation")
        self.assertEqual(database_action["action"], "confirm_credit")
        self.assertEqual(database_action["draft"]["CustomerName"], "Ramesh")
        self.assertEqual(database_action["draft"]["Amount"], 2500)
        self.assertEqual(understand_command.call_args.kwargs["customers"], ["Ramesh", "रमेश"])
        parse_and_execute.assert_not_called()

    def test_postgres_voice_customer_query_uses_hindi_alias(self):
        customer = SimpleNamespace(
            customer_id=4,
            customer_name="Ramesh",
            customer_name_hindi="रमेश",
            outstanding_balance=250,
        )
        with (
            patch("backend.app.main.current_store_id", return_value=7),
            patch(
                "backend.app.gemini_understanding.resolve_catalog_entity"
            ) as resolve_entity,
        ):
            result = main.build_postgres_voice_customer_result(
                {"action": "query_customer", "entity": "रमेश"},
                "रमेश का उधार कितना है",
                [customer],
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["CustomerName"], "Ramesh")
        self.assertEqual(result["data"]["OutstandingBalance"], 250)
        resolve_entity.assert_not_called()

    def test_postgres_voice_credit_keeps_spoken_new_customer_name(self):
        customer = SimpleNamespace(
            customer_id=9,
            customer_name="Avaneesh",
            customer_name_hindi=None,
            outstanding_balance=25,
        )
        with patch(
            "backend.app.gemini_understanding.resolve_catalog_entity",
            return_value="Avaneesh",
        ) as resolve_entity:
            result = main.build_postgres_voice_customer_result(
                {
                    "action": "credit",
                    "entity": "Avaneesh",
                    "quantity": "1000",
                    "phonetic_english_translation": "Aryan",
                },
                "aryan ke khaate mein 1000 rupay daal do",
                [customer],
            )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["CustomerName"], "Aryan")
        self.assertEqual(result["draft"]["Amount"], 1000)
        resolve_entity.assert_not_called()

    def test_postgres_voice_add_product_existing_item_returns_stock_confirmation(self):
        inventory = [{
            "ItemID": 3,
            "ItemName": "Maggi (MRP ₹14)",
            "ItemNameHindi": "मैगी",
            "StockQuantity": 20,
            "Price": 14,
        }]

        result = main.build_postgres_voice_product_result(
            {"action": "add_product", "entity": "मैगी", "quantity": "4"},
            "मैगी के 4 पैकेट जोड़ो",
            inventory,
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["Intent"], "restock")
        self.assertEqual(result["draft"]["ItemID"], 3)
        self.assertEqual(result["draft"]["CurrentStock"], 20)
        self.assertEqual(result["draft"]["Quantity"], 4)
        self.assertEqual(result["draft"]["StockMode"], "add")

    def test_postgres_voice_add_product_new_item_returns_price_search_draft(self):
        result = main.build_postgres_voice_product_result(
            {"action": "add_product", "entity": "New Tea", "quantity": "3"},
            "add 3 packets of new tea",
            [],
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["ItemName"], "New Tea")
        self.assertEqual(result["draft"]["StockQuantity"], 3)
        self.assertEqual(result["draft"]["SearchStatus"], "idle")
        self.assertEqual(result["draft"]["PriceOptions"], [])

    def test_postgres_stock_confirmation_supports_add_and_replace(self):
        item = SimpleNamespace(
            item_id=3,
            item_name="Maggi",
            stock_quantity=20,
            price=14,
        )
        with (
            main.app.app_context(),
            patch("backend.app.main.is_postgres_database", return_value=True),
            patch("backend.app.main.current_store_id", return_value=7),
            patch("backend.app.models.StoreInventory.query") as inventory_query,
            patch("backend.app.main.db.session.query") as session_query,
            patch("backend.app.main.db.session.add") as session_add,
            patch("backend.app.main.db.session.commit"),
        ):
            inventory_query.filter_by.return_value.with_for_update.return_value.first.return_value = item
            session_query.return_value.filter_by.return_value.scalar.return_value = 4
            client = main.app.test_client()

            add_response = client.post(
                "/api/inventory/confirm-command",
                json={
                    "ItemID": 3,
                    "Intent": "restock",
                    "Quantity": 5,
                    "StockMode": "add",
                },
            )
            replace_response = client.post(
                "/api/inventory/confirm-command",
                json={
                    "ItemID": 3,
                    "Intent": "restock",
                    "Quantity": 3,
                    "StockMode": "replace",
                },
            )

        self.assertEqual(add_response.status_code, 200)
        self.assertEqual(replace_response.status_code, 200)
        self.assertEqual(item.stock_quantity, 3)
        transactions = [call.args[0] for call in session_add.call_args_list]
        self.assertEqual(
            [(transaction.transaction_type, transaction.quantity) for transaction in transactions],
            [("Restock", 5), ("Stock Adjustment", -22)],
        )

    def test_postgres_voice_repayment_updates_customer_and_ledger(self):
        from backend.app.database import db
        from backend.app.models import StoreCredit, StoreTransaction

        customer = SimpleNamespace(
            customer_id=4,
            customer_name="Ramesh",
            customer_name_hindi="रमेश",
            outstanding_balance=250.0,
            is_active=True,
        )
        with (
            main.app.app_context(),
            patch("backend.app.main.current_store_id", return_value=7),
            patch("backend.app.models.StoreCredit.query") as customer_query,
            patch("backend.app.main.db.session.query") as session_query,
            patch("backend.app.main.db.session.add") as session_add,
            patch("backend.app.main.db.session.commit") as session_commit,
        ):
            customer_query.filter_by.return_value.with_for_update.return_value.first.return_value = customer
            session_query.return_value.filter_by.return_value.scalar.return_value = 9
            result = main.build_postgres_voice_customer_result(
                {"action": "repayment", "entity": "रमेश", "quantity": "100"},
                "Ramesh paid 100 rupees",
                [customer],
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "repayment_recorded")
        self.assertEqual(customer.outstanding_balance, 150)
        session_add.assert_called_once()
        transaction = session_add.call_args.args[0]
        self.assertEqual(transaction.store_id, 7)
        self.assertEqual(transaction.txn_id, 10)
        self.assertEqual(transaction.transaction_type, "Repayment")
        self.assertEqual(transaction.total_amount, -100)
        session_commit.assert_called_once()
        customer_query.filter_by.assert_called_once_with(
            store_id=7,
            customer_id=4,
            is_active=True,
        )

    @patch.dict(
        os.environ,
        {"GNANI_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"},
    )
    @patch("backend.app.services.query_service.QueryService")
    @patch("backend.app.main.parse_and_execute")
    @patch("backend.app.main.understand_command")
    @patch("backend.app.main.transcribe_audio", return_value="मैगी बेच दीजिए")
    def test_hindi_voice_command_does_not_repeat_hindi_transcription(
        self,
        transcribe_audio,
        understand_command,
        parse_and_execute,
        query_service,
    ):
        understand_command.return_value = {
            "action": "sell",
            "entity": "Maggi 70g",
            "quantity": 2,
            "spoken_response": "क्या मैं आगे बढ़ूँ?",
        }
        parse_and_execute.return_value = {
            "status": "pending_confirmation",
            "action": "confirm_sale",
            "message": "Confirm sale",
        }
        query_service.return_value.get_store_kpis.return_value = {}

        response = main.app.test_client().post(
            "/api/process-audio",
            data={
                "audio": (io.BytesIO(b"audio"), "command.wav"),
                "lang": "hi-IN",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transcribe_audio.call_count, 1)
        transcribe_audio.assert_called_once_with(
            ANY,
            language_code="hi-IN",
        )
        understand_command.assert_called_once()
        parse_and_execute.assert_called_once()

    @patch.dict(
        os.environ,
        {"GNANI_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"},
    )
    @patch("backend.app.services.query_service.QueryService")
    @patch(
        "backend.app.main.parse_and_execute",
        side_effect=GeminiUnderstandingError(
            "Gemini's API quota or rate limit was reached (429)."
        ),
    )
    @patch("backend.app.main.understand_command")
    @patch("backend.app.main.transcribe_audio", return_value="मैगी बेच दीजिए")
    def test_voice_route_surfaces_gemini_catalog_matching_errors(
        self,
        transcribe_audio,
        understand_command,
        parse_and_execute,
        query_service,
    ):
        understand_command.return_value = {
            "action": "sell",
            "entity": "मैगी",
            "quantity": 2,
        }
        query_service.return_value.get_store_kpis.return_value = {}

        response = main.app.test_client().post(
            "/api/process-audio",
            data={
                "audio": (io.BytesIO(b"audio"), "command.wav"),
                "lang": "hi-IN",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("quota or rate limit", response.get_json()["error"])
        parse_and_execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
