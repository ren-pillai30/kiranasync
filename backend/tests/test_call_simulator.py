import unittest
import sqlite3
import os
import json
import tempfile
import asyncio
from unittest.mock import MagicMock, AsyncMock

from backend.app.services.gnani_service import GnaniService
from backend.app.services.call_db_service import CallDBService
from backend.app.services.call_gemini_service import CallGeminiService
from backend.app.routers.call_router import call_websocket_endpoint, get_call_system_status, simulate_call_turn, SimulateCallRequest


class TestCallSimulatorServices(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite database file for isolation
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE Inventory (
                ItemID INTEGER PRIMARY KEY AUTOINCREMENT,
                ItemName TEXT NOT NULL UNIQUE,
                StockQuantity INTEGER NOT NULL,
                Price REAL NOT NULL,
                IsActive INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE CustomerCredit (
                CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                CustomerName TEXT NOT NULL UNIQUE,
                PhoneNumber TEXT,
                OutstandingBalance REAL DEFAULT 0.0,
                IsActive INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE Transactions (
                TxnID INTEGER PRIMARY KEY AUTOINCREMENT,
                Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                CommandText TEXT,
                TotalAmount REAL,
                TransactionType TEXT,
                EntityName TEXT,
                Quantity REAL
            )
        """)

        # Seed test items
        cursor.executemany(
            "INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)",
            [
                ("Tata Salt 1kg", 50, 25.0),
                ("Maggi 70g", 100, 14.0),
                ("Sugar 1kg", 20, 45.0),
            ],
        )
        cursor.execute(
            "INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES (?, ?)",
            ("Ramesh", 150.0),
        )
        conn.commit()
        conn.close()

        self.db_service = CallDBService(db_path=self.temp_db_path)

    def tearDown(self):
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def test_get_store_context(self):
        ctx = self.db_service.get_store_context()
        self.assertIn("inventory", ctx)
        self.assertIn("customers", ctx)
        self.assertEqual(len(ctx["inventory"]), 3)
        self.assertEqual(len(ctx["customers"]), 1)
        self.assertEqual(ctx["customers"][0]["CustomerName"], "Ramesh")

    def test_execute_order_cash(self):
        result = self.db_service.execute_order(
            items=[{"name": "Tata Salt 1kg", "quantity": 2}],
            customer_name="Walk-in",
            payment_mode="cash",
            raw_call_text="I want 2 packets of Tata Salt",
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_amount"], 50.0)

        # Verify stock was decremented
        conn = sqlite3.connect(self.temp_db_path)
        row = conn.execute("SELECT StockQuantity FROM Inventory WHERE ItemName = 'Tata Salt 1kg'").fetchone()
        self.assertEqual(row[0], 48)

        # Verify transaction logged
        txn = conn.execute("SELECT EntityName, Quantity, TotalAmount FROM Transactions WHERE TransactionType = 'Sale'").fetchone()
        self.assertIsNotNone(txn)
        self.assertEqual(txn[0], "Tata Salt 1kg")
        self.assertEqual(txn[1], 2)
        self.assertEqual(txn[2], 50.0)
        conn.close()

    def test_execute_order_insufficient_stock(self):
        result = self.db_service.execute_order(
            items=[{"name": "Tata Salt 1kg", "quantity": 999}],
            customer_name="Ramesh",
            payment_mode="cash",
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("Insufficient stock", result["message"])

    def test_execute_order_on_udhaar(self):
        result = self.db_service.execute_order(
            items=[{"name": "Maggi 70g", "quantity": 2}],
            customer_name="Ramesh",
            payment_mode="udhaar",
            raw_call_text="2 maggi on credit for Ramesh",
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_amount"], 28.0)
        self.assertEqual(result["payment_mode"], "udhaar")
        self.assertEqual(result["new_balance"], 178.0)  # 150 + 28 = 178

        # Verify CustomerCredit updated
        conn = sqlite3.connect(self.temp_db_path)
        cust = conn.execute("SELECT OutstandingBalance FROM CustomerCredit WHERE CustomerName = 'Ramesh'").fetchone()
        self.assertEqual(cust[0], 178.0)
        conn.close()

    def test_execute_credit_log(self):
        result = self.db_service.execute_credit_log(
            customer_name="Ramesh",
            amount=200.0,
            raw_call_text="Log 200 rs udhaar for Ramesh",
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["new_balance"], 350.0)  # 150 + 200 = 350

        # Verify transaction logged
        conn = sqlite3.connect(self.temp_db_path)
        txn = conn.execute("SELECT TotalAmount FROM Transactions WHERE TransactionType = 'Credit'").fetchone()
        self.assertIsNotNone(txn)
        self.assertEqual(txn[0], 200.0)
        conn.close()

    def test_execute_repayment(self):
        result = self.db_service.execute_repayment(
            customer_name="Ramesh",
            amount=50.0,
            raw_call_text="Ramesh repaid 50 rupees",
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["new_balance"], 100.0)  # 150 - 50 = 100

        # Verify transaction logged
        conn = sqlite3.connect(self.temp_db_path)
        txn = conn.execute("SELECT TotalAmount FROM Transactions WHERE TransactionType = 'Repayment'").fetchone()
        self.assertIsNotNone(txn)
        self.assertEqual(txn[0], -50.0)
        conn.close()

    def test_gnani_service_languages(self):
        gnani = GnaniService(api_key="dummy_key")
        self.assertIn("hi-IN", gnani.SUPPORTED_LANGUAGES)
        self.assertIn("en-IN", gnani.SUPPORTED_LANGUAGES)
        self.assertIn("ta-IN", gnani.SUPPORTED_LANGUAGES)
        self.assertIn("te-IN", gnani.SUPPORTED_LANGUAGES)

    def test_call_gemini_greetings(self):
        gemini = CallGeminiService()
        greeting_hi = gemini.generate_call_greeting("Ramesh", "hi-IN")
        self.assertIn("Ramesh", greeting_hi)
        self.assertIn("किराना", greeting_hi)

        greeting_en = gemini.generate_call_greeting("John", "en-IN")
        self.assertIn("John", greeting_en)
        self.assertIn("Kirana store", greeting_en)

    def test_rest_status_and_simulate(self):
        status = get_call_system_status()
        self.assertIn("model", status)
        self.assertIn("supported_languages", status)

        req = SimulateCallRequest(
            user_input="Namaste, do you have Tata Salt?",
            caller_name="Ramesh",
            language_code="en-IN",
        )
        sim_res = simulate_call_turn(req)
        self.assertEqual(sim_res["status"], "success")
        self.assertTrue(len(sim_res["reply_text"]) > 0)

    def test_websocket_endpoint_flow(self):
        class MockWebSocket:
            def __init__(self, incoming_messages):
                self.incoming = list(incoming_messages)
                self.sent = []
                self.accepted = False

            async def accept(self):
                self.accepted = True

            async def receive(self):
                if not self.incoming:
                    return {"type": "websocket.disconnect"}
                msg = self.incoming.pop(0)
                return {"type": "websocket.receive", "text": json.dumps(msg)}

            async def send_json(self, data):
                self.sent.append(data)

        incoming = [
            {"type": "start_call", "customer_name": "Ramesh", "language_code": "en-IN"},
            {"type": "text_input", "text": "What is the price of Tata Salt?", "language_code": "en-IN"},
            {"type": "end_call"},
        ]
        mock_ws = MockWebSocket(incoming)

        asyncio.run(call_websocket_endpoint(mock_ws))

        self.assertTrue(mock_ws.accepted)
        self.assertGreaterEqual(len(mock_ws.sent), 3)
        self.assertEqual(mock_ws.sent[0]["type"], "call_connected")
        self.assertEqual(mock_ws.sent[1]["type"], "call_response")
        self.assertEqual(mock_ws.sent[2]["type"], "call_ended")


if __name__ == "__main__":
    unittest.main()

