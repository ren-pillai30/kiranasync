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
        self.gemini_key_patch = patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""},
            clear=False,
        )
        self.gemini_key_patch.start()
        self.addCleanup(self.gemini_key_patch.stop)
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
                VALUES
                    ('Sugar 1kg', 5, 10),
                    ('Toothpaste', 110, 33),
                    ('Biscoff Biscuit', 20, 60),
                    ('GoodDay Biscuit', 30, 20);
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

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["Intent"], "sell")
        with closing(sqlite3.connect(self.database_path)) as connection:
            stock = connection.execute(
                "SELECT StockQuantity FROM Inventory WHERE ItemName = 'Sugar 1kg'"
            ).fetchone()[0]
            transaction_count = connection.execute("SELECT COUNT(*) FROM Transactions").fetchone()[0]
        self.assertEqual((stock, transaction_count), (5, 0))

    def test_gemini_resolves_variant_product_for_normal_voice_command(self):
        with patch(
            "backend.app.gemini_understanding.resolve_catalog_entity",
            return_value="Sugar 1kg",
        ):
            result = intent_parser.parse_and_execute(
                "मैगी बेच दो",
                interpretation={
                    "action": "sell",
                    "entity": "मैगी",
                    "quantity": 2,
                },
            )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["ItemName"], "Sugar 1kg")

    def test_devanagari_product_name_uses_gemini_translation_to_match_catalog(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price) "
                "VALUES ('Maggi 70g', 100, 14)"
            )
            connection.commit()

        with patch(
            "backend.app.gemini_understanding.resolve_catalog_entity",
            return_value="Maggi 70g",
        ) as resolve_entity:
            result = intent_parser.parse_and_execute(
                "पचास मैगी बेच दो",
                interpretation={
                    "action": "sell",
                    "entity": "मैगी",
                    "quantity": 50,
                    "local_translation": "50 Maggi sell please",
                    "phonetic_english_translation": "Maggi",
                },
            )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["action"], "confirm_sale")
        self.assertEqual(result["draft"]["ItemName"], "Maggi 70g")
        self.assertEqual(result["draft"]["Quantity"], 50)
        resolve_entity.assert_called_once()
        self.assertEqual(resolve_entity.call_args.args[0], "मैगी")
        self.assertEqual(
            resolve_entity.call_args.args[3]["raw_transcript"],
            "पचास मैगी बेच दो",
        )

    @patch("backend.app.services.query_service.QueryService")
    @patch(
        "backend.app.gemini_understanding.resolve_catalog_entity",
        return_value="Maggi 70g",
    )
    def test_voice_stock_query_uses_gemini_resolved_catalog_name(
        self,
        resolve_entity,
        query_service,
    ):
        query_service.return_value.get_inventory_stock.return_value = {
            "found": True,
            "message": "Maggi 70g: 100 in stock.",
        }

        result = intent_parser.parse_and_execute(
            "मैगी का स्टॉक कितना है",
            interpretation={"action": "query_stock", "entity": "मैगी"},
        )

        self.assertEqual(result["status"], "success")
        query_service.return_value.get_inventory_stock.assert_called_once_with("Maggi 70g")
        resolve_entity.assert_called_once()

    @patch("backend.app.services.query_service.QueryService")
    @patch(
        "backend.app.gemini_understanding.resolve_catalog_entity",
        return_value="Ramesh",
    )
    def test_voice_customer_balance_query_uses_gemini_resolved_customer(
        self,
        resolve_entity,
        query_service,
    ):
        query_service.return_value.get_customer_balance.return_value = {
            "found": True,
            "message": "Ramesh has an outstanding balance of ₹20.",
        }

        result = intent_parser.parse_and_execute(
            "रामेश का उधार कितना है",
            interpretation={"action": "query_customer", "entity": "रामेश"},
        )

        self.assertEqual(result["status"], "success")
        query_service.return_value.get_customer_balance.assert_called_once_with("Ramesh")
        resolve_entity.assert_called_once()

    @patch(
        "backend.app.gemini_understanding.resolve_catalog_entity",
        return_value="Ramesh",
    )
    def test_voice_credit_uses_gemini_resolved_existing_customer(self, resolve_entity):
        result = intent_parser.parse_and_execute(
            "Ramiz ke khate mein 100 jodo",
            interpretation={
                "action": "credit",
                "entity": "Ramiz",
                "quantity": 100,
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["CustomerName"], "Ramesh")
        resolve_entity.assert_called_once()

    @patch(
        "backend.app.gemini_understanding.resolve_catalog_entity",
        return_value="Ramesh",
    )
    def test_voice_repayment_uses_gemini_resolved_customer(self, resolve_entity):
        result = intent_parser.parse_and_execute(
            "रामेश ने 5 रुपये जमा किए",
            interpretation={
                "action": "repayment",
                "entity": "रामेश",
                "quantity": 5,
            },
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["CustomerName"], "Ramesh")
        resolve_entity.assert_called_once()

    def test_inventory_match_is_attempted_once_for_an_unresolved_voice_product(self):
        with patch(
            "backend.app.gemini_understanding.resolve_catalog_entity",
            return_value=None,
        ) as resolve_entity:
            result = intent_parser.parse_and_execute(
                "७० मैगी बेच २",
                interpretation={
                    "action": "sell",
                    "entity": "मैगी",
                    "quantity": 2,
                    "local_translation": "sell 2 Maggi",
                    "phonetic_english_translation": "Maggi",
                },
            )

        self.assertEqual(result["action"], "item_not_found")
        resolve_entity.assert_called_once()
        self.assertEqual(resolve_entity.call_args.args[0], "मैगी")

    def test_unresolved_hindi_sale_suggests_nearest_inventory_item_for_confirmation(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)",
                ("मैगी (MRP ₹14)", 100, 14),
            )
            connection.commit()

        with patch(
            "backend.app.gemini_understanding.resolve_catalog_entity",
            return_value=None,
        ):
            result = intent_parser.parse_and_execute(
                "५० मैगी बेच दो",
                interpretation={
                    "action": "sell",
                    "entity": "मैगी",
                    "quantity": 50,
                },
            )

        self.assertEqual(result["status"], "pending_selection")
        self.assertEqual(result["action"], "select_inventory_item")
        self.assertTrue(result["draft"]["NearestMatch"])
        self.assertEqual(result["draft"]["Quantity"], 50)
        self.assertEqual(
            [item["ItemName"] for item in result["draft"]["Candidates"]],
            ["मैगी (MRP ₹14)"],
        )
        with closing(sqlite3.connect(self.database_path)) as connection:
            stock = connection.execute(
                "SELECT StockQuantity FROM Inventory WHERE ItemName = ?",
                ("मैगी (MRP ₹14)",),
            ).fetchone()[0]
            transaction_count = connection.execute(
                "SELECT COUNT(*) FROM Transactions"
            ).fetchone()[0]
        self.assertEqual(stock, 100)
        self.assertEqual(transaction_count, 0)

    def test_unresolved_hindi_sale_shows_tied_variants_instead_of_guessing(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executemany(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)",
                [
                    ("मैगी (MRP ₹14)", 100, 14),
                    ("मैगी (MRP ₹20)", 50, 20),
                ],
            )
            connection.commit()

        with patch(
            "backend.app.gemini_understanding.resolve_catalog_entity",
            return_value=None,
        ):
            result = intent_parser.parse_and_execute(
                "मैगी बेच दो",
                interpretation={
                    "action": "sell",
                    "entity": "मैगी",
                    "quantity": 1,
                },
            )

        self.assertEqual(result["status"], "pending_selection")
        self.assertEqual(
            {item["ItemName"] for item in result["draft"]["Candidates"]},
            {"मैगी (MRP ₹14)", "मैगी (MRP ₹20)"},
        )

    def test_explicit_transcript_quantity_overrides_model_quantity(self):
        result = intent_parser.parse_and_execute(
            "12 toothpaste bech do",
            interpretation={
                "action": "sell",
                "entity": "Toothpaste",
                "quantity": 2,
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["action"], "confirm_sale")
        self.assertEqual(result["draft"]["Quantity"], 12)
        with closing(sqlite3.connect(self.database_path)) as connection:
            stock = connection.execute(
                "SELECT StockQuantity FROM Inventory WHERE ItemName = 'Toothpaste'"
            ).fetchone()[0]
            transaction_count = connection.execute(
                "SELECT COUNT(*) FROM Transactions WHERE EntityName = 'Toothpaste'"
            ).fetchone()[0]
        self.assertEqual((stock, transaction_count), (110, 0))

    def test_romanized_hindi_quantity_is_not_confused_with_command_word(self):
        result = intent_parser.parse_and_execute(
            "chaunsath toothpaste bech do",
            interpretation={
                "action": "sell",
                "entity": "Toothpaste",
                "quantity": 2,
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["action"], "confirm_sale")
        self.assertEqual(result["draft"]["Quantity"], 64)
        self.assertEqual(
            intent_parser.extract_explicit_quantity("chaunsath toothpaste bech do"),
            64,
        )

    def test_restock_does_not_fuzzy_match_different_brand(self):
        result = intent_parser.parse_and_execute(
            "50 goodday biscuit aayi hai",
            interpretation={
                "action": "restock",
                "entity": "GoodDay Biscuit",
                "quantity": 50,
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["ItemName"], "GoodDay Biscuit")

        result = intent_parser.parse_and_execute(
            "50 new biscuit aayi hai",
            interpretation={
                "action": "restock",
                "entity": "New Biscuit",
                "quantity": 50,
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["ItemName"], "New Biscuit")
        self.assertEqual(result["draft"]["SearchStatus"], "idle")

    def test_validated_restock_is_added_to_ledger(self):
        result = intent_parser.parse_and_execute(
            "restock two sugar",
            interpretation={
                "action": "restock",
                "entity": "Sugar 1kg",
                "quantity": 2,
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["Intent"], "restock")
        with closing(sqlite3.connect(self.database_path)) as connection:
            stock = connection.execute(
                "SELECT StockQuantity FROM Inventory WHERE ItemName = 'Sugar 1kg'"
            ).fetchone()[0]
            transaction_count = connection.execute("SELECT COUNT(*) FROM Transactions").fetchone()[0]
        self.assertEqual((stock, transaction_count), (5, 0))

    def test_remove_product_waits_for_confirmation_and_keeps_stock_unchanged(self):
        result = intent_parser.parse_and_execute(
            "remove expired sugar",
            interpretation={
                "action": "remove_product",
                "entity": "Sugar 1kg",
                "quantity": None,
                "reason": "expired",
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["EntityType"], "Product")
        self.assertEqual(result["draft"]["Reason"], "expired")
        with closing(sqlite3.connect(self.database_path)) as connection:
            stock, active = connection.execute(
                "SELECT StockQuantity, IsActive FROM Inventory WHERE ItemName = 'Sugar 1kg'"
            ).fetchone()
            transaction_count = connection.execute(
                "SELECT COUNT(*) FROM Transactions"
            ).fetchone()[0]
        self.assertEqual((stock, active, transaction_count), (5, 1, 0))

    def test_voice_add_customer_creates_zero_balance_account(self):
        result = intent_parser.parse_and_execute(
            "add Suresh as a customer",
            interpretation={
                "action": "add_customer",
                "entity": "Suresh",
                "quantity": None,
            },
        )

        self.assertEqual(result["status"], "success")
        with closing(sqlite3.connect(self.database_path)) as connection:
            customer = connection.execute(
                "SELECT OutstandingBalance, IsActive FROM CustomerCredit WHERE CustomerName = 'Suresh'"
            ).fetchone()
        self.assertEqual(customer, (0, 1))

    @patch(
        "backend.app.gemini_understanding.resolve_catalog_entity",
        return_value=None,
    )
    def test_voice_credit_for_unknown_customer_creates_customer_with_balance(self, resolve_entity):
        result = intent_parser.parse_and_execute(
            "श्याम के खाते में 1564 डाल दो",
            interpretation={
                "action": "credit",
                "entity": "श्याम",
                "quantity": 1564,
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["Intent"], "credit")
        with closing(sqlite3.connect(self.database_path)) as connection:
            customer = connection.execute(
                "SELECT OutstandingBalance FROM CustomerCredit WHERE CustomerName = 'श्याम'"
            ).fetchone()
        self.assertIsNone(customer)
        resolve_entity.assert_called_once()

    def test_voice_remove_customer_waits_for_confirmation(self):
        result = intent_parser.parse_and_execute(
            "remove Ramesh from the udhaar list",
            interpretation={
                "action": "remove_customer",
                "entity": "Ramesh",
                "quantity": None,
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["EntityType"], "Customer")
        self.assertEqual(result["draft"]["QuantityOrBalance"], 20)

    def test_voice_remove_customer_archives_without_confirmation_below_one_rupee(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                "UPDATE CustomerCredit SET OutstandingBalance = 0.75 WHERE CustomerName = 'Ramesh'"
            )
            connection.commit()

        result = intent_parser.parse_and_execute(
            "remove Ramesh from the udhaar list",
            interpretation={
                "action": "remove_customer",
                "entity": "Ramesh",
                "quantity": None,
            },
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "customer_archived")
        with closing(sqlite3.connect(self.database_path)) as connection:
            balance, active = connection.execute(
                "SELECT OutstandingBalance, IsActive FROM CustomerCredit WHERE CustomerName = 'Ramesh'"
            ).fetchone()
        self.assertEqual((balance, active), (0.75, 0))

    def test_voice_remove_customer_deletes_exact_zero_balance_row(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                "UPDATE CustomerCredit SET OutstandingBalance = 0 WHERE CustomerName = 'Ramesh'"
            )
            connection.commit()

        result = intent_parser.parse_and_execute(
            "remove Ramesh from the udhaar list",
            interpretation={
                "action": "remove_customer",
                "entity": "Ramesh",
                "quantity": None,
            },
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "customer_deleted")
        with closing(sqlite3.connect(self.database_path)) as connection:
            customer = connection.execute(
                "SELECT 1 FROM CustomerCredit WHERE CustomerName = 'Ramesh'"
            ).fetchone()
        self.assertIsNone(customer)

    @patch.object(intent_parser, "search_product_online")
    def test_voice_add_product_uses_product_confirmation_flow(self, search):
        search.return_value = {
            "ItemName": "New Tea",
            "Price": 25,
            "PriceFound": True,
            "SearchMessage": "Verify the suggested price.",
            "SearchResults": [],
        }
        result = intent_parser.parse_and_execute(
            "add new tea with 3 packets",
            interpretation={
                "action": "add_product",
                "entity": "New Tea",
                "quantity": 3,
            },
        )

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["draft"]["StockQuantity"], 3)

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
        self.assertIsNone(result["draft"]["Price"])
        self.assertEqual(result["draft"]["StockQuantity"], 3)
        self.assertEqual(result["draft"]["SearchStatus"], "idle")
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
