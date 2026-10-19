import os
import sqlite3
import tempfile
import unittest
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
