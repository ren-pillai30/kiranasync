import os
import sqlite3
import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch

from backend.app import intent_parser, main


class TransactionLedgerApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.db")
        connection = sqlite3.connect(self.database_path)
        try:
            connection.executescript(
                """
                CREATE TABLE Inventory (
                    ItemID INTEGER PRIMARY KEY AUTOINCREMENT,
                    ItemName TEXT NOT NULL UNIQUE,
                    StockQuantity INTEGER NOT NULL,
                    Price REAL NOT NULL
                );
                CREATE TABLE CustomerCredit (
                    CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                    CustomerName TEXT NOT NULL UNIQUE,
                    OutstandingBalance REAL DEFAULT 0
                );
                CREATE TABLE Transactions (
                    TxnID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    CommandText TEXT,
                    TotalAmount REAL
                );
                INSERT INTO Transactions (CommandText, TotalAmount)
                VALUES ('legacy sale', 25);
                """
            )
        finally:
            connection.close()
        self.database_patch = patch.object(
            intent_parser, "DB_PATH", self.database_path
        )
        self.database_patch.start()
        self.client = main.app.test_client()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def test_dashboard_includes_legacy_and_manual_transactions(self):
        response = self.client.get("/api/ledger")
        self.assertEqual(response.status_code, 200)
        ledger = response.get_json()
        self.assertEqual(len(ledger["transactions"]), 1)
        self.assertEqual(
            ledger["transactions"][0]["TransactionType"], "Transaction"
        )

        inventory_response = self.client.post(
            "/api/inventory/add",
            json={"ItemName": "Tea", "StockQuantity": 4, "Price": 12},
        )
        credit_response = self.client.post(
            "/api/credit/add",
            json={"CustomerName": "Asha", "Amount": 30},
        )
        self.assertEqual(inventory_response.status_code, 200)
        self.assertEqual(credit_response.status_code, 200)

        transactions = self.client.get("/api/ledger").get_json()["transactions"]
        self.assertEqual(len(transactions), 3)
        self.assertEqual(
            {
                (
                    item["TransactionType"],
                    item["EntityName"],
                    item["Quantity"],
                    item["TotalAmount"],
                )
                for item in transactions
            },
            {
                ("Transaction", None, None, 25),
                ("Restock", "Tea", 4, -48),
                ("Credit", "Asha", None, 30),
            },
        )

    def test_process_audio_auto_mode_tries_every_supported_language(self):
        interpretation = {
            "action": "sell",
            "entity": "Sugar",
            "quantity": 2,
            "transcript_index": 3,
        }
        with patch.object(
            main,
            "transcribe_audio",
            side_effect=lambda _path, language_code: f"recognized {language_code}",
        ) as transcribe, patch.object(
            main, "get_db_records", return_value=[]
        ), patch.object(
            main, "understand_command", return_value=interpretation
        ) as understand, patch.object(
            main,
            "parse_and_execute",
            return_value={
                "status": "pending_review",
                "action": "review_transaction",
                "draft": {
                    "Intent": "sell",
                    "EntityName": "Sugar",
                    "Quantity": 2,
                    "RawCommand": "spoken command",
                },
            },
        ) as execute:
            response = self.client.post(
                "/api/process-audio",
                data={
                    "audio": (BytesIO(b"audio"), "command.wav"),
                    "language_code": "auto",
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transcribe.call_count, len(main.STT_LANGUAGE_CODES))
        self.assertEqual(
            {call.args[1] for call in transcribe.call_args_list},
            set(main.STT_LANGUAGE_CODES),
        )
        candidates = understand.call_args.kwargs["transcripts"]
        self.assertEqual(
            [candidate["language_code"] for candidate in candidates],
            list(main.STT_LANGUAGE_CODES),
        )
        self.assertEqual(
            response.get_json()["transcript"],
            "recognized hi-IN",
        )
        self.assertEqual(response.get_json()["language_code"], "hi-IN")
        execute.assert_called_once_with(
            "recognized hi-IN",
            interpretation=interpretation,
            preview_only=True,
        )

    def test_process_audio_manual_language_uses_one_transcription(self):
        interpretation = {
            "action": "unknown",
            "entity": "",
            "quantity": None,
            "transcript_index": 0,
        }
        with patch.object(
            main,
            "transcribe_audio",
            return_value="தமிழில் கட்டளை",
        ) as transcribe, patch.object(
            main, "get_db_records", return_value=[]
        ), patch.object(
            main, "understand_command", return_value=interpretation
        ), patch.object(
            main,
            "parse_and_execute",
            return_value={
                "status": "pending_review",
                "action": "review_transaction",
                "draft": {
                    "Intent": "restock",
                    "EntityName": "Sugar",
                    "Quantity": 2,
                    "RawCommand": "spoken command",
                },
            },
        ):
            response = self.client.post(
                "/api/process-audio",
                data={
                    "audio": (BytesIO(b"audio"), "command.wav"),
                    "language_code": "ta-IN",
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        transcribe.assert_called_once()
        self.assertEqual(transcribe.call_args.kwargs["language_code"], "ta-IN")
        self.assertEqual(response.get_json()["language_code"], "ta-IN")

    def test_confirm_transaction_uses_user_corrected_amount(self):
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)",
                ("Sugar 1kg", 10, 5),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.post(
            "/api/confirm-transaction",
            json={
                "Intent": "sell",
                "EntityName": "Sugar 1kg",
                "Quantity": 3,
                "RawCommand": "sell one sugar",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["database_action"]["status"],
            "success",
        )
        connection = sqlite3.connect(self.database_path)
        try:
            stock = connection.execute(
                "SELECT StockQuantity FROM Inventory WHERE ItemName = 'Sugar 1kg'"
            ).fetchone()[0]
            transaction = connection.execute(
                """
                SELECT Quantity, TotalAmount FROM Transactions
                WHERE EntityName = 'Sugar 1kg'
                """
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(stock, 7)
        self.assertEqual(transaction, (3, 15))

    def test_confirm_transaction_rejects_invalid_amount(self):
        with patch.object(main, "parse_and_execute") as execute:
            response = self.client.post(
                "/api/confirm-transaction",
                json={
                    "Intent": "sell",
                    "EntityName": "Sugar 1kg",
                    "Quantity": 0,
                    "RawCommand": "sell sugar",
                },
            )

        self.assertEqual(response.status_code, 400)
        execute.assert_not_called()

    def test_manual_inventory_add_is_written_only_after_confirmed_review(self):
        response = self.client.post(
            "/api/confirm-transaction",
            json={
                "Intent": "inventory_add",
                "EntityName": "Tea",
                "Quantity": 4,
                "UnitPrice": 12.5,
                "RawCommand": "Added 4 Tea",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["database_action"]["status"], "success")
        connection = sqlite3.connect(self.database_path)
        try:
            product = connection.execute(
                "SELECT StockQuantity, Price FROM Inventory WHERE ItemName = 'Tea'"
            ).fetchone()
            transaction = connection.execute(
                """
                SELECT TransactionType, EntityName, Quantity, TotalAmount
                FROM Transactions
                WHERE EntityName = 'Tea'
                """
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(product, (4, 12.5))
        self.assertEqual(transaction, ("Restock", "Tea", 4, -50))

    def test_manual_customer_credit_add_is_written_after_confirmation(self):
        response = self.client.post(
            "/api/confirm-transaction",
            json={
                "Intent": "credit_add",
                "EntityName": "Asha",
                "Quantity": 300,
                "RawCommand": "Added credit for Asha",
            },
        )

        self.assertEqual(response.status_code, 200)
        connection = sqlite3.connect(self.database_path)
        try:
            balance = connection.execute(
                "SELECT OutstandingBalance FROM CustomerCredit WHERE CustomerName = 'Asha'"
            ).fetchone()[0]
            transaction = connection.execute(
                """
                SELECT TransactionType, TotalAmount
                FROM Transactions
                WHERE EntityName = 'Asha'
                """
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(balance, 300)
        self.assertEqual(transaction, ("Credit", 300))

    def test_process_audio_rejects_unsupported_language_code(self):
        with patch.object(main, "transcribe_audio") as transcribe:
            response = self.client.post(
                "/api/process-audio",
                data={
                    "audio": (BytesIO(b"audio"), "command.wav"),
                    "language_code": "xx-IN",
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 400)
        transcribe.assert_not_called()

    @patch.dict(os.environ, {"GNANI_API_KEY": "test-gnani-key"})
    @patch("backend.app.main.requests.post")
    def test_tts_uses_gnani_timbre_and_returns_wav_audio(self, post):
        post.return_value.content = b"RIFF fake wav"

        response = self.client.post(
            "/api/tts",
            json={"text": "Please confirm sale of two Sugar.", "language": "en-IN"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "audio/wav")
        self.assertEqual(response.data, b"RIFF fake wav")
        self.assertEqual(
            post.call_args.args[0],
            "https://api.vachana.ai/api/v1/tts/inference",
        )
        self.assertEqual(
            post.call_args.kwargs["headers"]["X-API-Key-ID"],
            "test-gnani-key",
        )
        self.assertEqual(
            post.call_args.kwargs["json"]["model"],
            "timbre-v3.0",
        )
        self.assertEqual(post.call_args.kwargs["json"]["voice"], "Shivani")

    @patch.dict(os.environ, {}, clear=True)
    @patch("backend.app.main.requests.post")
    def test_tts_reports_missing_gnani_api_key(self, post):
        response = self.client.post(
            "/api/tts",
            json={"text": "Please confirm.", "language": "en-IN"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("GNANI_API_KEY", response.get_json()["error"])
        post.assert_not_called()

    @patch("backend.app.main.requests.post")
    def test_tts_rejects_unsupported_language(self, post):
        response = self.client.post(
            "/api/tts",
            json={"text": "Please confirm.", "language": "xx-IN"},
        )

        self.assertEqual(response.status_code, 400)
        post.assert_not_called()

    def test_confirm_restock_requires_valid_mrp_and_quantity(self):
        response = self.client.post(
            "/api/inventory/confirm-restock",
            json={
                "ItemName": "Tea",
                "StockQuantity": 2,
                "Price": None,
            },
        )

        self.assertEqual(response.status_code, 400)
        connection = sqlite3.connect(self.database_path)
        try:
            item_count = connection.execute(
                "SELECT COUNT(*) FROM Inventory"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(item_count, 0)

    def test_confirm_restock_adds_each_selected_mrp_as_a_separate_item(self):
        response = self.client.post(
            "/api/inventory/confirm-restock",
            json={
                "ItemName": "Navratna Tel 500ml",
                "RawCommand": "add navratna oil",
                "Items": [
                    {"Price": 70, "Quantity": 100},
                    {"Price": 85, "Quantity": 40},
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        connection = sqlite3.connect(self.database_path)
        try:
            products = connection.execute(
                "SELECT ItemName, StockQuantity, Price FROM Inventory ORDER BY Price"
            ).fetchall()
            transactions = connection.execute(
                """
                SELECT EntityName, Quantity, TotalAmount
                FROM Transactions
                WHERE EntityName IS NOT NULL
                ORDER BY TxnID DESC
                """
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual(
            products,
            [
                ("Navratna Tel 500ml (MRP ₹70)", 100, 70),
                ("Navratna Tel 500ml (MRP ₹85)", 40, 85),
            ],
        )
        self.assertEqual(
            transactions,
            [
                ("Navratna Tel 500ml (MRP ₹85)", 40, -3400),
                ("Navratna Tel 500ml (MRP ₹70)", 100, -7000),
            ],
        )

    @patch("backend.app.intent_parser.search_product_online")
    def test_product_lookup_uses_edited_product_name(self, search):
        search.return_value = {
            "ItemName": "Hide Seek",
            "Price": 25,
            "PriceFound": True,
            "PriceIsMRP": True,
            "SearchStatus": "found_mrp",
            "SearchMessage": "Found MRP",
            "SearchResults": [],
        }

        response = self.client.post(
            "/api/product-lookup",
            json={"ItemName": "Hide Seek"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ItemName"], "Hide Seek")
        search.assert_called_once_with("Hide Seek")

    def test_confirm_inventory_command_updates_only_chosen_variant(self):
        connection = sqlite3.connect(self.database_path)
        try:
            connection.executemany(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)",
                [
                    ("Navratna Oil (MRP ₹400)", 50, 400),
                    ("Navratna Oil (MRP ₹500)", 20, 500),
                ],
            )
            selected_id = connection.execute(
                "SELECT ItemID FROM Inventory WHERE Price = 500"
            ).fetchone()[0]
            connection.commit()
        finally:
            connection.close()

        response = self.client.post(
            "/api/inventory/confirm-command",
            json={
                "ItemID": selected_id,
                "Intent": "sell",
                "Quantity": 2,
                "RawCommand": "sell two navratna oil",
            },
        )

        self.assertEqual(response.status_code, 200)
        connection = sqlite3.connect(self.database_path)
        try:
            stocks = connection.execute(
                "SELECT StockQuantity FROM Inventory WHERE ItemName LIKE 'Navratna Oil%' ORDER BY Price"
            ).fetchall()
            ledger_entry = connection.execute(
                """
                SELECT EntityName, Quantity, TotalAmount
                FROM Transactions
                WHERE EntityName LIKE 'Navratna Oil%'
                """
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(stocks, [(50,), (18,)])
        self.assertEqual(ledger_entry, ("Navratna Oil (MRP ₹500)", 2, 1000))


if __name__ == "__main__":
    unittest.main()
