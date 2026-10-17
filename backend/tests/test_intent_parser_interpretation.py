import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

from backend.app import intent_parser
from ddgs.exceptions import DDGSException


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
        with closing(sqlite3.connect(self.database_path)) as connection:
            transaction = connection.execute(
                """
                SELECT TransactionType, EntityName, Quantity, TotalAmount
                FROM Transactions
                """
            ).fetchone()
        self.assertEqual(transaction, ("Sale", "Sugar 1kg", 2, 20))

    def test_validated_restock_is_added_to_ledger(self):
        result = intent_parser.parse_and_execute(
            "restock two sugar",
            interpretation={
                "action": "restock",
                "entity": "Sugar 1kg",
                "quantity": 2,
            },
        )

        self.assertEqual(result["status"], "success")
        with closing(sqlite3.connect(self.database_path)) as connection:
            transaction = connection.execute(
                """
                SELECT TransactionType, EntityName, Quantity, TotalAmount
                FROM Transactions
                """
            ).fetchone()
        self.assertEqual(transaction, ("Restock", "Sugar 1kg", 2, -20))

    def test_sale_of_ambiguous_mrp_variants_waits_for_product_choice(self):
        connection = sqlite3.connect(self.database_path)
        try:
            connection.executemany(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)",
                [
                    ("Navratna Oil (MRP ₹400)", 50, 400),
                    ("Navratna Oil (MRP ₹500)", 20, 500),
                ],
            )
            connection.commit()
        finally:
            connection.close()

        result = intent_parser.parse_and_execute(
            "pachas liter navratna tel bech do",
            interpretation={
                "action": "sell",
                "entity": "Navratna Oil (MRP ₹400)",
                "quantity": 50,
            },
        )

        self.assertEqual(result["status"], "pending_selection")
        self.assertEqual(result["action"], "select_inventory_item")
        self.assertEqual(
            {candidate["ItemName"] for candidate in result["draft"]["Candidates"]},
            {"Navratna Oil (MRP ₹400)", "Navratna Oil (MRP ₹500)"},
        )
        with closing(sqlite3.connect(self.database_path)) as connection:
            stocks = connection.execute(
                "SELECT StockQuantity FROM Inventory WHERE ItemName LIKE 'Navratna Oil%' ORDER BY Price"
            ).fetchall()
            transaction_count = connection.execute(
                "SELECT COUNT(*) FROM Transactions"
            ).fetchone()[0]
        self.assertEqual(stocks, [(50,), (20,)])
        self.assertEqual(transaction_count, 0)

    @patch.object(intent_parser, "search_product_online")
    def test_new_product_restock_waits_for_price_confirmation(self, search):
        search.return_value = {
            "ItemName": "New Tea",
            "Price": 24.5,
            "PriceFound": True,
            "SearchMessage": "Suggested price found online. Verify the MRP before adding.",
            "SearchResults": [{"Title": "New Tea MRP", "URL": "https://example.test"}],
        }
        result = intent_parser.parse_and_execute(
            "new tea 3 pieces arrived",
            interpretation={
                "action": "restock",
                "entity": "New Tea",
                "quantity": 3,
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["ItemName"], "New Tea")
        self.assertEqual(result["draft"]["Price"], 24.5)
        self.assertEqual(result["draft"]["StockQuantity"], 3)
        self.assertEqual(len(result["draft"]["SearchResults"]), 1)
        with closing(sqlite3.connect(self.database_path)) as connection:
            item_count = connection.execute(
                "SELECT COUNT(*) FROM Inventory WHERE ItemName = 'New Tea'"
            ).fetchone()[0]
            transaction_count = connection.execute(
                "SELECT COUNT(*) FROM Transactions"
            ).fetchone()[0]
        self.assertEqual((item_count, transaction_count), (0, 0))

    @patch.object(intent_parser, "DDGS")
    def test_web_lookup_prefers_mrp_and_returns_result_source(self, ddgs_class):
        ddgs = ddgs_class.return_value.__enter__.return_value
        ddgs.text.side_effect = [
            [{
                "title": "New Tea offer ₹18; MRP ₹25",
                "body": "Pack of 100g",
                "href": "https://example.test/new-tea",
            }]
            for _ in range(3)
        ]

        result = intent_parser.search_product_online("new tea")

        self.assertEqual(result["Price"], 25)
        self.assertTrue(result["PriceFound"])
        self.assertTrue(result["PriceIsMRP"])
        self.assertEqual(result["SearchStatus"], "found_mrp")
        self.assertEqual(result["PriceOptions"][0]["Price"], 25)
        self.assertTrue(result["PriceOptions"][0]["PriceIsMRP"])
        self.assertEqual(
            result["SearchResults"][0]["URL"],
            "https://example.test/new-tea",
        )

    @patch.object(intent_parser, "DDGS")
    def test_web_lookup_excludes_unrelated_sources_and_prices(self, ddgs_class):
        ddgs = ddgs_class.return_value.__enter__.return_value
        ddgs.text.side_effect = [[
            {
                "title": "Martin Luther quote",
                "body": "We need to hear the Gospel every day",
                "href": "https://example.test/quote",
            },
            {
                "title": "Top quotes",
                "body": "₹50 quote collection",
                "href": "https://example.test/quotes",
            },
        ]] * 3

        result = intent_parser.search_product_online("Hid Seek")

        self.assertFalse(result["PriceFound"])
        self.assertIsNone(result["Price"])
        self.assertEqual(result["SearchStatus"], "no_relevant_results")
        self.assertEqual(result["SearchResults"], [])

    @patch.object(intent_parser, "DDGS")
    def test_web_lookup_matches_product_name_with_spoken_n_connector(self, ddgs_class):
        ddgs = ddgs_class.return_value.__enter__.return_value
        ddgs.text.side_effect = [[
            {
                "title": "Parle Hide & Seek Chocolate Chip Biscuits MRP ₹35",
                "body": "Hide & Seek biscuits",
                "href": "https://example.test/hide-seek",
            },
            {
                "title": "Martin Luther quotes",
                "body": "Hide and seek from the Gospel ₹100",
                "href": "https://example.test/quotes",
            },
        ]] * 3

        result = intent_parser.search_product_online("Hide N Seek")

        self.assertEqual(result["Price"], 35)
        self.assertTrue(result["PriceIsMRP"])
        self.assertEqual(result["PriceOptions"][0]["Price"], 35)
        self.assertEqual(
            [source["URL"] for source in result["SearchResults"]],
            ["https://example.test/hide-seek"],
        )

    @patch.object(intent_parser, "DDGS")
    def test_web_lookup_ignores_generic_product_type_terms(self, ddgs_class):
        ddgs = ddgs_class.return_value.__enter__.return_value
        ddgs.text.side_effect = [
            [],
            [{
                "title": "Parle Hide & Seek Chocolate Chip MRP ₹35",
                "body": "Chocolate biscuits",
                "href": "https://example.test/hide-seek",
            }],
            [],
        ]

        result = intent_parser.search_product_online("Hide And Seek Biscuit")

        self.assertEqual(result["Price"], 35)
        self.assertEqual(
            [source["URL"] for source in result["SearchResults"]],
            ["https://example.test/hide-seek"],
        )
        self.assertEqual(ddgs.text.call_count, 3)

    @patch.object(intent_parser, "DDGS")
    def test_web_lookup_continues_when_a_query_has_no_results(self, ddgs_class):
        ddgs = ddgs_class.return_value.__enter__.return_value
        ddgs.text.side_effect = DDGSException("No results found.")

        result = intent_parser.search_product_online("Hide And Seek Biscuit")

        self.assertEqual(result["SearchStatus"], "no_relevant_results")
        self.assertEqual(ddgs.text.call_count, 3)

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
