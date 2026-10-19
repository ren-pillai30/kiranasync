import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

from backend.app import intent_parser
from backend.app.main import app
from backend.app.intent_parser import get_db_records
from backend.app.services.entity_service import EntityService


class EntityServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "entities.db")
        with closing(sqlite3.connect(self.database_path)) as conn:
            conn.executescript(
                """
                CREATE TABLE Inventory (
                    ItemID INTEGER PRIMARY KEY,
                    ItemName TEXT UNIQUE,
                    StockQuantity INTEGER NOT NULL,
                    Price REAL NOT NULL
                );
                CREATE TABLE CustomerCredit (
                    CustomerID INTEGER PRIMARY KEY,
                    CustomerName TEXT UNIQUE,
                    OutstandingBalance REAL DEFAULT 0
                );
                INSERT INTO Inventory (ItemID, ItemName, StockQuantity, Price)
                VALUES (1, 'Milk 1L', 4, 30);
                INSERT INTO CustomerCredit (CustomerID, CustomerName, OutstandingBalance)
                VALUES (1, 'Ramesh', 75);
                """
            )
        self.service = EntityService(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_archive_product_writes_off_stock_and_retains_ledger(self):
        result = self.service.archive_inventory_item(1, "recalled", "remove recalled milk")

        self.assertEqual(result["status"], "success")
        with closing(sqlite3.connect(self.database_path)) as conn:
            item = conn.execute(
                "SELECT StockQuantity, IsActive FROM Inventory WHERE ItemID = 1"
            ).fetchone()
            transaction = conn.execute(
                "SELECT TransactionType, EntityName, Quantity, TotalAmount, CommandText FROM Transactions"
            ).fetchone()
        self.assertEqual(item, (0, 0))
        self.assertEqual(transaction[:4], ("WriteOff", "Milk 1L", 4, -120))
        self.assertIn("recalled", transaction[4])
        audit_records = self.service.list_archives()
        self.assertEqual(len(audit_records), 1)
        self.assertEqual(audit_records[0]["EntityName"], "Milk 1L")
        self.assertEqual(audit_records[0]["Reason"], "recalled")
        self.assertEqual(audit_records[0]["Quantity"], 4)
        self.assertEqual(
            get_db_records("Inventory", "ItemName", db_path=self.database_path),
            [],
        )

    def test_archive_customer_preserves_balance_and_records_removal(self):
        result = self.service.archive_customer(1, "requested", "remove Ramesh")

        self.assertEqual(result["status"], "success")
        with closing(sqlite3.connect(self.database_path)) as conn:
            customer = conn.execute(
                "SELECT OutstandingBalance, IsActive FROM CustomerCredit WHERE CustomerID = 1"
            ).fetchone()
            transaction = conn.execute(
                "SELECT TransactionType, EntityName FROM Transactions"
            ).fetchone()
        self.assertEqual(customer, (75, 0))
        self.assertEqual(transaction, ("CustomerArchived", "Ramesh"))
        audit_records = self.service.list_archives()
        self.assertEqual(len(audit_records), 1)
        self.assertEqual(audit_records[0]["Balance"], 75)
        self.assertEqual(
            get_db_records("CustomerCredit", "CustomerName", db_path=self.database_path),
            [],
        )

    def test_remove_zero_balance_customer_deletes_row_but_keeps_audit_history(self):
        with closing(sqlite3.connect(self.database_path)) as conn:
            conn.execute(
                "UPDATE CustomerCredit SET OutstandingBalance = 0 WHERE CustomerID = 1"
            )
            conn.execute(
                """
                CREATE TABLE Aliases (
                    AliasID INTEGER PRIMARY KEY,
                    EntityType TEXT,
                    EntityID INTEGER,
                    ResolvedName TEXT,
                    SpokenAlias TEXT UNIQUE
                )
                """
            )
            conn.execute(
                "INSERT INTO Aliases (EntityType, EntityID, ResolvedName, SpokenAlias) "
                "VALUES ('Customer', 1, 'Ramesh', 'rameshu')"
            )
            conn.commit()

        result = self.service.archive_customer(1, raw_command="remove Ramesh")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "customer_deleted")
        with closing(sqlite3.connect(self.database_path)) as conn:
            self.assertIsNone(
                conn.execute(
                    "SELECT 1 FROM CustomerCredit WHERE CustomerID = 1"
                ).fetchone()
            )
            self.assertIsNone(
                conn.execute("SELECT 1 FROM Aliases WHERE EntityID = 1").fetchone()
            )
            transaction = conn.execute(
                "SELECT TransactionType, EntityName FROM Transactions"
            ).fetchone()
        self.assertEqual(transaction, ("CustomerArchived", "Ramesh"))

    def test_archive_api_routes_confirmed_customer_removal(self):
        with patch.object(intent_parser, "DB_PATH", self.database_path):
            client = app.test_client()
            response = client.post(
                "/api/entities/archive",
                json={"EntityType": "Customer", "EntityID": 1, "Reason": "manual removal"},
            )
            audit_response = client.get("/api/archives")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "success")
        self.assertEqual(audit_response.status_code, 200)
        audit_records = audit_response.get_json()["archives"]
        self.assertEqual(len(audit_records), 1)
        self.assertEqual(audit_records[0]["EntityName"], "Ramesh")
        self.assertEqual(audit_records[0]["Reason"], "manual removal")
        with closing(sqlite3.connect(self.database_path)) as conn:
            archived = conn.execute(
                "SELECT IsActive, OutstandingBalance FROM CustomerCredit WHERE CustomerID = 1"
            ).fetchone()
        self.assertEqual(archived, (0, 75))


if __name__ == "__main__":
    unittest.main()
