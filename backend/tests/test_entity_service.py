import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app import intent_parser
from backend.app import main
from backend.app.main import app
from backend.app.intent_parser import get_db_records
from backend.app.models import StoreCredit, StoreEntityArchive
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

    def test_archive_customer_removes_account_and_records_balance_in_audit(self):
        result = self.service.archive_customer(1, "requested", "remove Ramesh")

        self.assertEqual(result["status"], "success")
        with closing(sqlite3.connect(self.database_path)) as conn:
            customer = conn.execute(
                "SELECT 1 FROM CustomerCredit WHERE CustomerID = 1"
            ).fetchone()
            transaction = conn.execute(
                "SELECT TransactionType, EntityName FROM Transactions"
            ).fetchone()
        self.assertIsNone(customer)
        self.assertEqual(transaction, ("CustomerArchived", "Ramesh"))
        audit_records = self.service.list_archives()
        self.assertEqual(len(audit_records), 1)
        self.assertEqual(audit_records[0]["Balance"], 75)
        self.assertEqual(
            get_db_records("CustomerCredit", "CustomerName", db_path=self.database_path),
            [],
        )

    def test_readding_removed_customer_starts_with_new_balance(self):
        self.service.archive_customer(1, "requested", "remove Ramesh")
        with patch.object(intent_parser, "DB_PATH", self.database_path):
            app.config["LOGIN_DISABLED"] = True
            response = app.test_client().post(
                "/api/credit/add",
                json={
                    "CustomerName": "Ramesh",
                    "CustomerNameHindi": "रमेश",
                    "Amount": 20,
                },
            )

        self.assertEqual(response.status_code, 200)
        with closing(sqlite3.connect(self.database_path)) as conn:
            customer = conn.execute(
                "SELECT OutstandingBalance, IsActive FROM CustomerCredit "
                "WHERE CustomerName = 'Ramesh'"
            ).fetchone()
        self.assertEqual(customer, (20, 1))
        audit_records = self.service.list_archives()
        self.assertEqual(len(audit_records), 1)
        self.assertEqual(audit_records[0]["Balance"], 75)

    def test_readding_legacy_inactive_customer_does_not_restore_stale_balance(self):
        self.service.list_archives()
        with closing(sqlite3.connect(self.database_path)) as conn:
            conn.execute(
                "UPDATE CustomerCredit SET IsActive = 0 WHERE CustomerID = 1"
            )
            conn.commit()
        with patch.object(intent_parser, "DB_PATH", self.database_path):
            app.config["LOGIN_DISABLED"] = True
            response = app.test_client().post(
                "/api/credit/add",
                json={"CustomerName": "Ramesh", "Amount": 20},
            )

        self.assertEqual(response.status_code, 200)
        with closing(sqlite3.connect(self.database_path)) as conn:
            customer = conn.execute(
                "SELECT OutstandingBalance, IsActive FROM CustomerCredit "
                "WHERE CustomerName = 'Ramesh'"
            ).fetchone()
        self.assertEqual(customer, (20, 1))

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
            app.config["LOGIN_DISABLED"] = True
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
        self.assertIsNone(archived)

    def test_postgres_customer_removal_records_balance_audit_and_deletes_account(self):
        customer = SimpleNamespace(
            customer_id=4,
            customer_name="Ramesh",
            outstanding_balance=75,
            is_active=True,
        )
        customer_query = MagicMock()
        customer_query.filter_by.return_value.first.return_value = customer
        transaction_query = MagicMock()
        transaction_query.filter_by.return_value.scalar.return_value = 3

        with (
            app.app_context(),
            app.test_client() as client,
            patch.dict(app.config, {"TESTING": True, "LOGIN_DISABLED": True}),
            patch("backend.app.main.is_postgres_database", return_value=True),
            patch("backend.app.main.current_store_id", return_value=7),
            patch.object(StoreCredit, "query", customer_query),
            patch("backend.app.main.db.session.query", return_value=transaction_query),
            patch("backend.app.main.db.session.add") as session_add,
            patch("backend.app.main.db.session.flush"),
            patch("backend.app.main.db.session.delete") as session_delete,
            patch("backend.app.main.db.session.commit") as session_commit,
        ):
            response = client.post(
                "/api/entities/archive",
                json={
                    "EntityType": "Customer",
                    "EntityID": 4,
                    "Reason": "requested",
                    "RawCommand": "remove Ramesh",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["action"], "customer_deleted")
        self.assertEqual(response.get_json()["status"], "success")
        archive = next(
            value for (value,), _ in session_add.call_args_list
            if isinstance(value, StoreEntityArchive)
        )
        self.assertEqual(archive.store_id, 7)
        self.assertEqual(archive.entity_name, "Ramesh")
        self.assertEqual(archive.balance, 75)
        self.assertEqual(archive.reason, "requested")
        session_delete.assert_called_once_with(customer)
        session_commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
