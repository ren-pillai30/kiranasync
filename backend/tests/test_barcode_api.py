import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backend.app import intent_parser, main


class BarcodeApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "barcode_test.db")
        connection = sqlite3.connect(self.database_path)
        try:
            connection.executescript(
                """
                CREATE TABLE Inventory (
                    ItemID INTEGER PRIMARY KEY AUTOINCREMENT,
                    ItemName TEXT NOT NULL UNIQUE,
                    StockQuantity INTEGER NOT NULL,
                    Price REAL NOT NULL,
                    Barcode TEXT,
                    IsActive INTEGER DEFAULT 1
                );
                CREATE TABLE CustomerCredit (
                    CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                    CustomerName TEXT NOT NULL UNIQUE,
                    OutstandingBalance REAL DEFAULT 0,
                    IsActive INTEGER DEFAULT 1
                );
                CREATE TABLE Transactions (
                    TxnID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    CommandText TEXT,
                    TotalAmount REAL
                );
                CREATE TABLE Aliases (
                    AliasID INTEGER PRIMARY KEY AUTOINCREMENT,
                    EntityType TEXT,
                    EntityID INTEGER,
                    ResolvedName TEXT,
                    SpokenAlias TEXT UNIQUE,
                    IsApproved INTEGER DEFAULT 1,
                    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO Inventory (ItemName, StockQuantity, Price, Barcode, IsActive)
                VALUES ('Parle-G 100g', 50, 10.0, '8901719101037', 1);
                """
            )
        finally:
            connection.close()

        self.database_patch = patch.object(intent_parser, "DB_PATH", self.database_path)
        self.database_patch.start()
        main.app.config["LOGIN_DISABLED"] = True
        self.client = main.app.test_client()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def test_barcode_lookup_finds_registered_item(self):
        response = self.client.get("/api/barcode/lookup?code=8901719101037")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("found"))
        self.assertEqual(data["item"]["ItemName"], "Parle-G 100g")
        self.assertEqual(data["item"]["Price"], 10.0)

    def test_barcode_lookup_handles_unknown_code(self):
        response = self.client.get("/api/barcode/lookup?code=9999999999999")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data.get("found"))

    def test_barcode_link_associates_new_barcode(self):
        response = self.client.post(
            "/api/barcode/link",
            json={"ItemID": 1, "Barcode": "1234567890123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "success")

        # Now lookup should succeed
        lookup_res = self.client.get("/api/barcode/lookup?code=1234567890123")
        self.assertEqual(lookup_res.status_code, 200)
        lookup_data = lookup_res.get_json()
        self.assertTrue(lookup_data.get("found"))
        self.assertEqual(lookup_data["item"]["ItemName"], "Parle-G 100g")


if __name__ == "__main__":
    unittest.main()
