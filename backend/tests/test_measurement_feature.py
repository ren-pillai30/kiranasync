import unittest
from unittest.mock import patch
from backend.app import intent_parser
from backend.app.services.call_db_service import CallDBService
import sqlite3
import tempfile
import os


class TestMeasurementFeature(unittest.TestCase):
    @patch.object(intent_parser, "DDGS")
    def test_search_product_online_measurement_mismatch(self, ddgs_class):
        # User searches for 1 kg of salt, but web results only have 300g, 500g, 2 kg
        ddgs = ddgs_class.return_value.__enter__.return_value
        ddgs.text.side_effect = [
            [
                {
                    "title": "Tata Salt 500g Pouch MRP ₹15",
                    "body": "Buy Tata Salt 500g online in India at best price.",
                    "href": "https://example.com/salt-500g",
                },
                {
                    "title": "Tata Salt 2kg Family Pack MRP ₹50",
                    "body": "Vacuum evaporated iodised salt 2kg.",
                    "href": "https://example.com/salt-2kg",
                },
                {
                    "title": "Tata Salt 300g Table Shaker MRP ₹25",
                    "body": "300g salt shaker container.",
                    "href": "https://example.com/salt-300g",
                },
            ]
            for _ in range(5)
        ]

        result = intent_parser.search_product_online("1 kg salt")

        self.assertFalse(result["ExactMeasurementFound"])
        self.assertEqual(result["RequestedMeasurement"], "1 kg")
        self.assertEqual(result["SearchStatus"], "measurement_mismatch")
        self.assertIn("300 g", result["AvailableMeasurements"])
        self.assertIn("500 g", result["AvailableMeasurements"])
        self.assertIn("2 kg", result["AvailableMeasurements"])
        self.assertIn("Exact measurement (1 kg) is not available", result["SearchMessage"])
        self.assertIn("Exact measurement 1 kg is not available", result["SpeechMessage"])
        self.assertIn("500 g", result["SpeechMessage"])

    @patch.object(intent_parser, "DDGS")
    def test_search_product_online_exact_measurement_found(self, ddgs_class):
        # User searches for 1 kg of salt, and web results DO have 1 kg
        ddgs = ddgs_class.return_value.__enter__.return_value
        ddgs.text.side_effect = [
            [
                {
                    "title": "Tata Salt 1kg Pack MRP ₹28",
                    "body": "Standard 1kg Tata Salt pouch MRP Rs 28.",
                    "href": "https://example.com/salt-1kg",
                },
            ]
            for _ in range(5)
        ]

        result = intent_parser.search_product_online("1 kg salt")

        self.assertTrue(result["ExactMeasurementFound"])
        self.assertEqual(result["SearchStatus"], "found_mrp")
        self.assertEqual(result["Price"], 28.0)

    def test_call_db_service_order_measurement_mismatch(self):
        # Create temp sqlite db with 500g and 2kg salt, but NOT 1kg
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE Inventory (ItemID INTEGER PRIMARY KEY, ItemName TEXT, StockQuantity INTEGER, Price REAL, IsActive INTEGER DEFAULT 1)"
            )
            conn.execute(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price, IsActive) VALUES ('Tata Salt 500g', 20, 15.0, 1)"
            )
            conn.execute(
                "INSERT INTO Inventory (ItemName, StockQuantity, Price, IsActive) VALUES ('Tata Salt 2kg', 10, 50.0, 1)"
            )
            conn.commit()
            conn.close()

            service = CallDBService(db_path=db_path)
            res = service.execute_order(
                items=[{"name": "1 kg salt", "quantity": 1}],
                customer_name="Ramesh",
                payment_mode="cash",
            )

            self.assertEqual(res["status"], "measurement_mismatch")
            self.assertEqual(res["requested_measurement"], "1 kg")
            self.assertIn("500 g", res["other_measurements"])
            self.assertIn("2 kg", res["other_measurements"])
            self.assertIn("Exact measurement (1 kg) is not available", res["message"])
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
