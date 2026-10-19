import os
import sqlite3
import tempfile
import unittest

from backend.app.services.alias_service import AliasService, ensure_aliases_schema
from backend.app.intent_parser import ensure_transactions_schema, parse_and_execute

class AliasIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_alias.db")
        conn = sqlite3.connect(self.db_path)
        ensure_transactions_schema(conn)
        ensure_aliases_schema(conn)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS Inventory (ItemID INTEGER PRIMARY KEY AUTOINCREMENT, ItemName TEXT UNIQUE, StockQuantity INTEGER, Price REAL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS CustomerCredit (CustomerID INTEGER PRIMARY KEY AUTOINCREMENT, CustomerName TEXT UNIQUE, OutstandingBalance REAL)")
        
        # Seed test items & customers
        cursor.execute("INSERT INTO Inventory (ItemID, ItemName, StockQuantity, Price) VALUES (1, 'Maggi 70g', 50, 14.0)")
        cursor.execute("INSERT INTO Inventory (ItemID, ItemName, StockQuantity, Price) VALUES (2, 'Tata Salt 1kg', 40, 25.0)")
        cursor.execute("INSERT INTO CustomerCredit (CustomerID, CustomerName, OutstandingBalance) VALUES (1, 'Ramesh', 200.0)")
        cursor.execute("INSERT INTO CustomerCredit (CustomerID, CustomerName, OutstandingBalance) VALUES (2, 'Suresh', 0.0)")
        conn.commit()
        conn.close()

        self.service = AliasService(self.db_path)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_add_alias_validates_target_id_existence(self):
        """Cannot add alias for non-existent product or customer ID."""
        res_bad_prod = self.service.add_alias("Product", 999, "Fake Item", "noodles")
        self.assertEqual(res_bad_prod["status"], "error")
        self.assertIn("does not exist", res_bad_prod["error"])

        res_bad_cust = self.service.add_alias("Customer", 888, "Fake Customer", "bhaiya")
        self.assertEqual(res_bad_cust["status"], "error")
        self.assertIn("does not exist", res_bad_cust["error"])

        res_ok = self.service.add_alias("Product", 1, "Maggi 70g", "noodles")
        self.assertEqual(res_ok["status"], "success")

    def test_add_alias_rejects_conflicting_mappings(self):
        """Reject remapping an existing alias to a different entity."""
        # 1. Add alias 'namak' -> Tata Salt (ID 2)
        res1 = self.service.add_alias("Product", 2, "Tata Salt 1kg", "namak")
        self.assertEqual(res1["status"], "success")

        # 2. Try to map 'namak' -> Maggi (ID 1)
        res_conflict = self.service.add_alias("Product", 1, "Maggi 70g", "namak")
        self.assertEqual(res_conflict["status"], "error")
        self.assertIn("Conflicting alias", res_conflict["error"])

        # 3. Same mapping is idempotent
        res_same = self.service.add_alias("Product", 2, "Tata Salt 1kg", "namak")
        self.assertEqual(res_same["status"], "success")

    def test_resolve_alias_verifies_target_still_exists(self):
        """Resolving an alias fails gracefully if target entity was deleted."""
        self.service.add_alias("Product", 2, "Tata Salt 1kg", "safed namak")
        
        # Delete item from inventory
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM Inventory WHERE ItemID = 2")
        conn.commit()
        conn.close()

        resolved = self.service.resolve_alias("safed namak")
        self.assertFalse(resolved["Found"])
        self.assertIn("no longer exists", resolved["Error"])

    def test_parse_and_execute_resolves_alias_in_real_pipeline(self):
        """parse_and_execute successfully resolves aliases in production pipeline."""
        self.service.add_alias("Product", 1, "Maggi 70g", "2-minute")

        # Interpretation using alias
        interp = {
            "action": "sell",
            "entity": "2-minute",
            "quantity": 3
        }
        res = parse_and_execute("3 packet 2-minute bech do", interpretation=interp, db_path=self.db_path)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "inventory_updated")
        self.assertIn("Maggi 70g", res["message"])

        # Verify stock decremented
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT StockQuantity FROM Inventory WHERE ItemID = 1")
        stock = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(stock, 47)

if __name__ == '__main__':
    unittest.main()
