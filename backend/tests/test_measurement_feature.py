import unittest
from unittest.mock import patch
from backend.app import intent_parser
from backend.app.services.call_db_service import CallDBService
import sqlite3
import tempfile
import os


class TestMeasurementFeature(unittest.TestCase):
    @patch.object(intent_parser, "DDGS")
    def test_search_product_online_measurement_mismatch(self, ddgs_class):
        # User searches for 1 kg of salt, but web results only have 300g, 500g, 2 kg
        ddgs = ddgs_class.return_value.__enter__.return_value
        ddgs.text.side_effect = [
            [
                {
                    "title": "Tata Salt 500g Pouch MRP ₹15",
                    "body": "Buy Tata Salt 500g online in India at best price.",
                    "href": "https://example.com/salt-500g",
                },
                {
                    "title": "Tata Salt 2kg Family Pack MRP ₹50",
                    "body": "Vacuum evaporated iodised salt 2kg.",
                    "href": "https://example.com/salt-2kg",
                },
                {
                    "title": "Tata Salt 300g Table Shaker MRP ₹25",
                    "body": "300g salt shaker container.",
                    "href": "https://example.com/salt-300g",
                },
            ]
            for _ in range(5)
        ]

        result = intent_parser.search_product_online("1 kg salt")

        self.assertFalse(result["ExactMeasurementFound"])
        self.assertEqual(result["RequestedMeasurement"], "1 kg")
        self.assertEqual(result["SearchStatus"], "measurement_mismatch")
        self.assertIn("300 g", result["AvailableMeasurements"])
        self.assertIn("500 g", result["AvailableMeasurements"])
        self.assertIn("2 kg", result["AvailableMeasurements"])
        self.assertIn("Exact measurement (1 kg) is not available", result["SearchMessage"])
        self.assertIn("Exact measurement 1 kg is not available", result["SpeechMessage"])
        self.assertIn("500 g", result["SpeechMessage"])

    @patch.object(intent_parser, "DDGS")
    def test_search_product_online_exact_measurement_found(self, ddgs_class):
        # User searches for 1 kg of salt, and web results DO have 1 kg
        ddgs = ddgs_class.return_value.__enter__.return_value
        ddgs.text.side_effect = [
            [
                {
                    "title": "Tata Salt 1kg Pack MRP ₹28",
                    "body": "Standard 1kg Tata Salt pouch MRP Rs 28.",
                    "href": "https://example.com/salt-1kg",
                },
            ]
            for _ in range(5)
        ]

        result = intent_parser.search_product_online("1 kg salt")

        self.assertTrue(result["ExactMeasurementFound"])
        self.assertEqual(result["SearchStatus"], "found_mrp")
        self.assertEqual(result["Price"], 28.0)

    def test_call_db_service_order_measurement_mismatch(self):
        # Create temp sqlite db with 500g and 2kg salt, but NOT 1kg
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE Inventory (ItemID INTEGER PRIMARY KEY, ItemName TEXT, StockQuantity INTEGER, Price REAL, IsActive INTEGER DEFAULT 1)"
            )
            conn.execute(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price, IsActive) VALUES ('Tata Salt 500g', 20, 15.0, 1)"
            )
            conn.execute(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price, IsActive) VALUES ('Tata Salt 2kg', 10, 50.0, 1)"
            )
            conn.commit()
            conn.close()

            service = CallDBService(db_path=db_path)
            res = service.execute_order(
                items=[{"name": "1 kg salt", "quantity": 1}],
                customer_name="Ramesh",
                payment_mode="cash",
            )

            self.assertEqual(res["status"], "measurement_mismatch")
            self.assertEqual(res["requested_measurement"], "1 kg")
            self.assertIn("500 g", res["other_measurements"])
            self.assertIn("2 kg", res["other_measurements"])
            self.assertIn("Exact measurement (1 kg) is not available", res["message"])
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_voice_command_measurement_mismatch_does_not_transact(self):
        # Store only has Tata Salt 1kg in inventory. Voice command asks for 1.5 kg salt.
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE Inventory (ItemID INTEGER PRIMARY KEY, ItemName TEXT, StockQuantity INTEGER, Price REAL, IsActive INTEGER DEFAULT 1)"
            )
            conn.execute(
                "CREATE TABLE CustomerCredit (CustomerID INTEGER PRIMARY KEY, CustomerName TEXT, OutstandingBalance REAL, IsActive INTEGER DEFAULT 1)"
            )
            conn.execute(
                "CREATE TABLE Transactions (rowid INTEGER PRIMARY KEY AUTOINCREMENT, Timestamp TEXT, CommandText TEXT, TotalAmount REAL, TransactionType TEXT, EntityName TEXT, Quantity INTEGER)"
            )
            conn.execute(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price, IsActive) VALUES ('Tata Salt 1kg', 10, 28.0, 1)"
            )
            conn.commit()
            conn.close()

            with patch("backend.app.intent_parser.DB_PATH", db_path):
                res = intent_parser.parse_and_execute(
                    "1.5 kg salt becho",
                    interpretation={
                        "action": "sell",
                        "entity": "1.5 kg salt",
                        "quantity": 1,
                    },
                    db_path=db_path,
                )

                self.assertEqual(res["status"], "failed")
                self.assertEqual(res["action"], "measurement_mismatch")
                self.assertIn("1.5 kg", res["message"])
                self.assertIn("Only 1 kg is currently in the inventory", res["message"])
                self.assertIn("1.5 kg", res["speech_message"])
                self.assertIn("1 kg currently in the inventory", res["speech_message"])

                # Verify 1 kg was NOT transacted
                conn = sqlite3.connect(db_path)
                stock = conn.execute("SELECT StockQuantity FROM Inventory WHERE ItemName = 'Tata Salt 1kg'").fetchone()[0]
                txn_count = conn.execute("SELECT COUNT(*) FROM Transactions").fetchone()[0]
                conn.close()

                self.assertEqual(stock, 10, "Stock must remain 10 — 1 kg must NOT be transacted!")
                self.assertEqual(txn_count, 0, "No transactions should be recorded on measurement mismatch!")

        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_voice_command_exact_measurement_transacts_normally(self):
        # Store has Tata Salt 1kg. Voice command asks for 1 kg salt.
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE Inventory (ItemID INTEGER PRIMARY KEY, ItemName TEXT, StockQuantity INTEGER, Price REAL, IsActive INTEGER DEFAULT 1)"
            )
            conn.execute(
                "CREATE TABLE CustomerCredit (CustomerID INTEGER PRIMARY KEY, CustomerName TEXT, OutstandingBalance REAL, IsActive INTEGER DEFAULT 1)"
            )
            conn.execute(
                "CREATE TABLE Transactions (rowid INTEGER PRIMARY KEY AUTOINCREMENT, Timestamp TEXT, CommandText TEXT, TotalAmount REAL, TransactionType TEXT, EntityName TEXT, Quantity INTEGER)"
            )
            conn.execute(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price, IsActive) VALUES ('Tata Salt 1kg', 10, 28.0, 1)"
            )
            conn.commit()
            conn.close()

            with patch("backend.app.intent_parser.DB_PATH", db_path):
                res = intent_parser.parse_and_execute(
                    "1 kg salt becho",
                    interpretation={
                        "action": "sell",
                        "entity": "1 kg salt",
                        "quantity": 1,
                    },
                    db_path=db_path,
                )

                self.assertEqual(res["status"], "success")

                # Verify 1 kg was transacted
                conn = sqlite3.connect(db_path)
                stock = conn.execute("SELECT StockQuantity FROM Inventory WHERE ItemName = 'Tata Salt 1kg'").fetchone()[0]
                txn_count = conn.execute("SELECT COUNT(*) FROM Transactions").fetchone()[0]
                conn.close()

                self.assertEqual(stock, 9, "Stock should decrement to 9!")
                self.assertEqual(txn_count, 1, "Transaction should be recorded!")

        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()

