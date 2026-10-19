import os
import sqlite3
import tempfile
import unittest
from backend.app.services.command_service import CommandService
from backend.app.services.transaction_service import TransactionService
from backend.app.services.query_service import QueryService, ensure_v2_schema

class RetailAccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "retail_test.db")
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
            INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES ('Maggi 70g', 50, 14.0);
            INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES ('Suresh', 300.0);
        """)
        conn.commit()
        ensure_v2_schema(conn)
        conn.close()

        self.cmd_service = CommandService(self.db_path)
        self.query_service = QueryService(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_udhaar_sale_decrements_stock_and_increases_debt_atomically(self):
        """UdhaarSale must reduce inventory and increase customer debt in one atomic commit."""
        draft = self.cmd_service.create_pending_command("udhaar_sale", {
            "ItemID": 1,
            "Quantity": 5,
            "CustomerName": "Suresh",
            "RawCommand": "5 Maggi Suresh ke udhaar me likh do"
        })
        res = self.cmd_service.confirm_command(draft["CommandID"], TransactionService.commit_udhaar_sale)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["NewStock"], 45) # 50 - 5
        self.assertEqual(res["NewBalance"], 370.0) # 300 + (5 * 14)

        conn = sqlite3.connect(self.db_path)
        stock = conn.execute("SELECT StockQuantity FROM Inventory WHERE ItemID = 1").fetchone()[0]
        bal = conn.execute("SELECT OutstandingBalance FROM CustomerCredit WHERE CustomerName = 'Suresh'").fetchone()[0]
        txn = conn.execute("SELECT TransactionType, Quantity, TotalAmount FROM Transactions").fetchone()
        conn.close()

        self.assertEqual(stock, 45)
        self.assertEqual(bal, 370.0)
        self.assertEqual(txn, ("UdhaarSale", 5, 70.0))

    def test_repayment_reduces_debt_safely(self):
        """Repayment reduces customer balance and prevents silent overpayment."""
        draft = self.cmd_service.create_pending_command("repayment", {
            "CustomerName": "Suresh",
            "Amount": 200.0,
            "RawCommand": "Suresh ne 200 rupaye diye"
        })
        res = self.cmd_service.confirm_command(draft["CommandID"], TransactionService.commit_repayment)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["NewBalance"], 100.0) # 300 - 200

        conn = sqlite3.connect(self.db_path)
        bal = conn.execute("SELECT OutstandingBalance FROM CustomerCredit WHERE CustomerName = 'Suresh'").fetchone()[0]
        txn = conn.execute("SELECT TransactionType, TotalAmount FROM Transactions").fetchone()
        conn.close()

        self.assertEqual(bal, 100.0)
        self.assertEqual(txn, ("Repayment", 200.0))

    def test_overpayment_rejected_without_explicit_approval(self):
        """Payment greater than balance must be rejected by default to prevent silent negative debt."""
        draft = self.cmd_service.create_pending_command("repayment", {
            "CustomerName": "Suresh",
            "Amount": 500.0 # Suresh only owes 300
        })
        res = self.cmd_service.confirm_command(draft["CommandID"], TransactionService.commit_repayment)
        self.assertEqual(res["status"], "error")
        self.assertIn("exceeds Suresh's balance", res["error"])

        conn = sqlite3.connect(self.db_path)
        bal = conn.execute("SELECT OutstandingBalance FROM CustomerCredit WHERE CustomerName = 'Suresh'").fetchone()[0]
        txns_count = conn.execute("SELECT count(*) FROM Transactions").fetchone()[0]
        conn.close()

        self.assertEqual(bal, 300.0)
        self.assertEqual(txns_count, 0)

    def test_hisaab_summary_distinguishes_cash_udhaar_and_repayment(self):
        """Hisaab summary aggregates metrics accurately according to retail accounting rules."""
        # 1. Cash sale of 10 Maggi (₹140)
        draft1 = self.cmd_service.create_pending_command("sale", {"ItemID": 1, "Quantity": 10})
        self.cmd_service.confirm_command(draft1["CommandID"], TransactionService.commit_sale)

        # 2. Udhaar sale of 5 Maggi (₹70)
        draft2 = self.cmd_service.create_pending_command("udhaar_sale", {"ItemID": 1, "Quantity": 5, "CustomerName": "Suresh"})
        self.cmd_service.confirm_command(draft2["CommandID"], TransactionService.commit_udhaar_sale)

        # 3. Repayment of ₹100
        draft3 = self.cmd_service.create_pending_command("repayment", {"CustomerName": "Suresh", "Amount": 100.0})
        self.cmd_service.confirm_command(draft3["CommandID"], TransactionService.commit_repayment)

        hisaab = self.query_service.get_today_hisaab()
        self.assertEqual(hisaab["CashSalesTotal"], 140.0)
        self.assertEqual(hisaab["UdhaarSalesTotal"], 70.0)
        self.assertEqual(hisaab["RepaymentsTotal"], 100.0)
        self.assertEqual(hisaab["TotalRevenue"], 210.0) # 140 + 70
        self.assertEqual(hisaab["CashCollected"], 240.0) # 140 + 100
        self.assertEqual(hisaab["TotalOutstandingDebt"], 270.0) # 300 + 70 - 100

if __name__ == '__main__':
    unittest.main()
