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
        with sqlite3.connect(self.database_path) as connection:
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
