import os
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app import main
from backend.app.models import (
    StoreCredit,
    StoreEntityArchive,
    StoreInventory,
    StoreTransaction,
)


class StoreResetTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "store.db")
        connection = sqlite3.connect(self.database_path)
        try:
            connection.executescript(
                """
                CREATE TABLE Inventory (ItemID INTEGER PRIMARY KEY AUTOINCREMENT, ItemName TEXT);
                CREATE TABLE CustomerCredit (CustomerID INTEGER PRIMARY KEY AUTOINCREMENT, CustomerName TEXT);
                CREATE TABLE Transactions (TxnID INTEGER PRIMARY KEY AUTOINCREMENT, CommandText TEXT);
                CREATE TABLE EntityArchive (ArchiveID INTEGER PRIMARY KEY AUTOINCREMENT, EntityName TEXT);
                CREATE TABLE Aliases (AliasID INTEGER PRIMARY KEY AUTOINCREMENT, SpokenAlias TEXT);
                CREATE TABLE PendingCommands (CommandID TEXT PRIMARY KEY);
                INSERT INTO Inventory VALUES (1, 'Tea');
                INSERT INTO CustomerCredit VALUES (1, 'Asha');
                INSERT INTO Transactions VALUES (1, 'Sale');
                INSERT INTO EntityArchive VALUES (1, 'Old item');
                INSERT INTO Aliases VALUES (1, 'chai');
                INSERT INTO PendingCommands VALUES ('pending-1');
                """
            )
        finally:
            connection.close()
        self.store = SimpleNamespace(
            name="Old Shop",
            phone="123",
            address="Old address",
            city="Old city",
            register_opening_balance=500,
            setup_complete=True,
        )
        self.owner = SimpleNamespace(
            is_authenticated=True,
            email="ARYAN.PILLAI2024@VITSTUDENT.AC.IN",
            role="owner",
            store_id=17,
            store=self.store,
        )
        self.client = main.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_owner_reset_clears_store_data_and_profile_but_keeps_account(self):
        with (
            patch.dict(main.app.config, {"TESTING": True}),
            patch("backend.app.auth.current_user", self.owner),
            patch("backend.app.auth.is_postgres_database", return_value=False),
            patch(
                "backend.app.intent_parser.get_store_db_path",
                return_value=self.database_path,
            ),
            patch("backend.app.auth.db.session.commit"),
        ):
            response = self.client.post(
                "/api/store/reset",
                json={"confirmation": "RESET"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "success")
        self.assertEqual(self.owner.email, "ARYAN.PILLAI2024@VITSTUDENT.AC.IN")
        self.assertEqual(self.store.name, "My Store")
        self.assertIsNone(self.store.phone)
        self.assertIsNone(self.store.address)
        self.assertIsNone(self.store.city)
        self.assertEqual(self.store.register_opening_balance, 0)
        self.assertFalse(self.store.setup_complete)
        connection = sqlite3.connect(self.database_path)
        try:
            for table in (
                "Inventory",
                "CustomerCredit",
                "Transactions",
                "EntityArchive",
                "Aliases",
                "PendingCommands",
            ):
                count = connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
                self.assertEqual(count, 0, table)
            sequences = connection.execute(
                "SELECT COUNT(*) FROM sqlite_sequence"
            ).fetchone()[0]
            self.assertEqual(sequences, 0)
        finally:
            connection.close()

    def test_other_accounts_cannot_reset_store(self):
        other_user = SimpleNamespace(
            is_authenticated=True,
            email="another@example.com",
            role="owner",
            store_id=17,
            store=self.store,
        )
        with (
            patch.dict(main.app.config, {"TESTING": True}),
            patch("backend.app.auth.current_user", other_user),
            patch("backend.app.auth.db.session.commit") as commit,
        ):
            response = self.client.post(
                "/api/store/reset",
                json={"confirmation": "RESET"},
            )

        self.assertEqual(response.status_code, 403)
        commit.assert_not_called()
        connection = sqlite3.connect(self.database_path)
        try:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM Inventory").fetchone()[0],
                1,
            )
        finally:
            connection.close()

    def test_reset_requires_explicit_confirmation(self):
        with (
            patch.dict(main.app.config, {"TESTING": True}),
            patch("backend.app.auth.current_user", self.owner),
            patch("backend.app.auth.db.session.commit") as commit,
        ):
            response = self.client.post(
                "/api/store/reset",
                json={"confirmation": "reset"},
            )

        self.assertEqual(response.status_code, 400)
        commit.assert_not_called()

    def test_postgres_reset_deletes_only_current_store_rows(self):
        models = (
            StoreInventory,
            StoreCredit,
            StoreTransaction,
            StoreEntityArchive,
        )
        query_mocks = []
        delete_mocks = []
        query_patches = []
        with main.app.app_context():
            try:
                for model in models:
                    query_patch = patch.object(model, "query")
                    query_patches.append(query_patch)
                    query_mock = query_patch.start()
                    query_mocks.append(query_mock)
                    delete_mocks.append(query_mock.filter_by.return_value.delete)

                with (
                    patch.dict(main.app.config, {"TESTING": True}),
                    patch("backend.app.auth.current_user", self.owner),
                    patch("backend.app.auth.is_postgres_database", return_value=True),
                    patch(
                        "backend.app.intent_parser.get_store_db_path",
                        return_value=self.database_path,
                    ),
                    patch("backend.app.auth.db.session.commit"),
                ):
                    response = self.client.post(
                        "/api/store/reset",
                        json={"confirmation": "RESET"},
                    )
            finally:
                for query_patch in reversed(query_patches):
                    query_patch.stop()

        self.assertEqual(response.status_code, 200)
        for delete_mock in delete_mocks:
            delete_mock.assert_called_once_with(synchronize_session=False)
        for query_mock in query_mocks:
            query_mock.filter_by.assert_called_once_with(store_id=17)


if __name__ == "__main__":
    unittest.main()
