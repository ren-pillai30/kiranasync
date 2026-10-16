import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

from backend.app import intent_parser


class IntentParserInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.db")
        connection = sqlite3.connect(self.database_path)
        try:
            connection.executescript(
                """
                CREATE TABLE Inventory (
                    ItemID INTEGER PRIMARY KEY,
                    ItemName TEXT,
                    StockQuantity INTEGER,
                    Price INTEGER
                );
                CREATE TABLE CustomerCredit (
                    CustomerID INTEGER PRIMARY KEY,
                    CustomerName TEXT,
                    OutstandingBalance INTEGER
                );
                CREATE TABLE Transactions (
                    TransactionID INTEGER PRIMARY KEY,
                    CommandText TEXT,
                    TotalAmount INTEGER
                );
                INSERT INTO Inventory (ItemName, StockQuantity, Price)
                VALUES ('Sugar 1kg', 5, 10);
                INSERT INTO CustomerCredit (CustomerName, OutstandingBalance)
                VALUES ('Ramesh', 20);
                """
            )
            connection.commit()
        finally:
            connection.close()
        self.database_patch = patch.object(
            intent_parser,
            "DB_PATH",
            self.database_path,
        )
        self.database_patch.start()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def test_validated_sale_updates_stock(self):
        result = intent_parser.parse_and_execute(
            "do sugar bech do",
            interpretation={
                "action": "sell",
                "entity": "Sugar 1kg",
                "quantity": 2,
            },
        )

        self.assertEqual(result["status"], "success")
        with closing(sqlite3.connect(self.database_path)) as connection:
            stock = connection.execute(
                "SELECT StockQuantity FROM Inventory WHERE ItemName = 'Sugar 1kg'"
            ).fetchone()[0]
        self.assertEqual(stock, 3)

    def test_unknown_action_does_not_change_stock_or_balance(self):
        result = intent_parser.parse_and_execute(
            "some unclear command",
            interpretation={
                "action": "unknown",
                "entity": "",
                "quantity": None,
            },
        )

        self.assertEqual(result["action"], "intent_unrecognized")
        with closing(sqlite3.connect(self.database_path)) as connection:
            stock = connection.execute(
                "SELECT StockQuantity FROM Inventory WHERE ItemName = 'Sugar 1kg'"
            ).fetchone()[0]
            balance = connection.execute(
                "SELECT OutstandingBalance FROM CustomerCredit WHERE CustomerName = 'Ramesh'"
            ).fetchone()[0]
            transactions = connection.execute(
                "SELECT COUNT(*) FROM Transactions"
            ).fetchone()[0]
        self.assertEqual((stock, balance, transactions), (5, 20, 0))

    def test_missing_quantity_does_not_change_stock(self):
        result = intent_parser.parse_and_execute(
            "sugar bech do",
            interpretation={
                "action": "sell",
                "entity": "Sugar 1kg",
                "quantity": None,
            },
        )

        self.assertEqual(result["action"], "quantity_unrecognized")
        with closing(sqlite3.connect(self.database_path)) as connection:
            stock = connection.execute(
                "SELECT StockQuantity FROM Inventory WHERE ItemName = 'Sugar 1kg'"
            ).fetchone()[0]
        self.assertEqual(stock, 5)


if __name__ == "__main__":
    unittest.main()
