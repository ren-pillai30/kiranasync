import os
import sqlite3
import tempfile
import unittest
from backend.app.services.command_service import CommandService
from backend.app.services.transaction_service import TransactionService

class TrustSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "trust_test.db")
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE Inventory (
                ItemID INTEGER PRIMARY KEY AUTOINCREMENT,
                ItemName TEXT NOT NULL UNIQUE,
                StockQuantity INTEGER NOT NULL DEFAULT 0,
                Price REAL NOT NULL DEFAULT 0.0
            );
            CREATE TABLE CustomerCredit (
                CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                CustomerName TEXT NOT NULL UNIQUE,
                OutstandingBalance REAL NOT NULL DEFAULT 0.0
            );
            CREATE TABLE Transactions (
                TxnID INTEGER PRIMARY KEY AUTOINCREMENT,
                Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                CommandText TEXT,
                TotalAmount REAL,
                TransactionType TEXT,
                EntityName TEXT,
                Quantity REAL
            );
            INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES ('Tata Salt 1kg', 10, 25.0);
            INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES ('Ramesh', 100.0);
        """)
        conn.commit()
        conn.close()
        self.service = CommandService(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_unconfirmed_draft_does_not_mutate_inventory(self):
        """A draft command MUST NOT modify stock before confirmation."""
        draft = self.service.create_pending_command("sale", {
            "ItemID": 1,
            "Quantity": 3,
            "RawCommand": "3 Tata Salt bech do"
        })
        self.assertEqual(draft["Status"], "PENDING")

        # Verify database stock was NOT touched
        conn = sqlite3.connect(self.db_path)
        stock = conn.execute("SELECT StockQuantity FROM Inventory WHERE ItemID = 1").fetchone()[0]
        txns = conn.execute("SELECT count(*) FROM Transactions").fetchone()[0]
        conn.close()

        self.assertEqual(stock, 10)
        self.assertEqual(txns, 0)

    def test_cancelled_draft_does_not_mutate_data(self):
        """A cancelled draft MUST NOT modify stock."""
        draft = self.service.create_pending_command("sale", {
            "ItemID": 1,
            "Quantity": 5
        })
        cancel_res = self.service.cancel_command(draft["CommandID"])
        self.assertEqual(cancel_res["status"], "success")

        # Attempt to confirm after cancel must fail
        confirm_res = self.service.confirm_command(draft["CommandID"], TransactionService.commit_sale)
        self.assertEqual(confirm_res["status"], "error")
        self.assertIn("cannot be committed", confirm_res["error"])

        conn = sqlite3.connect(self.db_path)
        stock = conn.execute("SELECT StockQuantity FROM Inventory WHERE ItemID = 1").fetchone()[0]
        conn.close()
        self.assertEqual(stock, 10)

    def test_confirmed_sale_mutates_stock_atomically(self):
        """Confirming a sale atomically reduces stock and writes to ledger."""
        draft = self.service.create_pending_command("sale", {
            "ItemID": 1,
            "Quantity": 4,
            "RawCommand": "4 Tata Salt bech do"
        })
        confirm_res = self.service.confirm_command(draft["CommandID"], TransactionService.commit_sale)
        self.assertEqual(confirm_res["status"], "success")
        self.assertFalse(confirm_res["idempotent"])
        self.assertEqual(confirm_res["NewStock"], 6)

        conn = sqlite3.connect(self.db_path)
        stock = conn.execute("SELECT StockQuantity FROM Inventory WHERE ItemID = 1").fetchone()[0]
        txn = conn.execute("SELECT TransactionType, EntityName, Quantity, TotalAmount FROM Transactions").fetchone()
        conn.close()

        self.assertEqual(stock, 6)
        self.assertEqual(txn, ("Sale", "Tata Salt 1kg", 4, 100.0))

    def test_duplicate_confirmation_is_idempotent(self):
        """Submitting confirmation multiple times MUST NOT double-decrement stock."""
        draft = self.service.create_pending_command("sale", {
            "ItemID": 1,
            "Quantity": 2,
            "RawCommand": "2 Tata Salt bech do"
        })
        first_confirm = self.service.confirm_command(draft["CommandID"], TransactionService.commit_sale)
        self.assertEqual(first_confirm["status"], "success")
        self.assertFalse(first_confirm["idempotent"])

        # Second confirm with the same command ID
        second_confirm = self.service.confirm_command(draft["CommandID"], TransactionService.commit_sale)
        self.assertEqual(second_confirm["status"], "success")
        self.assertTrue(second_confirm["idempotent"])

        conn = sqlite3.connect(self.db_path)
        stock = conn.execute("SELECT StockQuantity FROM Inventory WHERE ItemID = 1").fetchone()[0]
        txns_count = conn.execute("SELECT count(*) FROM Transactions").fetchone()[0]
        conn.close()

        # Stock should be 8 (10 - 2), NOT 6 (10 - 2 - 2)
        self.assertEqual(stock, 8)
        self.assertEqual(txns_count, 1)

    def test_insufficient_stock_revalidation_rejects_safely(self):
        """If stock drops below requested quantity between draft and confirm, confirmation fails safely."""
        draft = self.service.create_pending_command("sale", {
            "ItemID": 1,
            "Quantity": 8
        })

        # Simulate concurrent purchase that reduces stock to 5
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE Inventory SET StockQuantity = 5 WHERE ItemID = 1")
        conn.commit()
        conn.close()

        # Confirming the draft for 8 must be rejected
        confirm_res = self.service.confirm_command(draft["CommandID"], TransactionService.commit_sale)
        self.assertEqual(confirm_res["status"], "error")
        self.assertIn("Insufficient stock", confirm_res["error"])

        conn = sqlite3.connect(self.db_path)
        stock = conn.execute("SELECT StockQuantity FROM Inventory WHERE ItemID = 1").fetchone()[0]
        txns_count = conn.execute("SELECT count(*) FROM Transactions").fetchone()[0]
        conn.close()

        self.assertEqual(stock, 5)
        self.assertEqual(txns_count, 0)

if __name__ == '__main__':
    unittest.main()
