import unittest
from backend.app.measurement_utils import (
    extract_measurement,
    extract_all_measurements,
    strip_measurement,
    are_measurements_equal,
    analyze_measurement_matches,
)


class TestMeasurementUtils(unittest.TestCase):
    def test_extract_measurement(self):
        m1 = extract_measurement("1 kg salt")
        self.assertIsNotNone(m1)
        self.assertEqual(m1["raw_value"], 1.0)
        self.assertEqual(m1["base_value"], 1000.0)
        self.assertEqual(m1["display"], "1 kg")

        m2 = extract_measurement("500g sugar")
        self.assertIsNotNone(m2)
        self.assertEqual(m2["base_value"], 500.0)
        self.assertEqual(m2["display"], "500 g")

        m3 = extract_measurement("2 litre milk")
        self.assertIsNotNone(m3)
        self.assertEqual(m3["base_value"], 2000.0)
        self.assertEqual(m3["display"], "2 L")

    def test_equivalence(self):
        m1 = extract_measurement("1 kg")
        m2 = extract_measurement("1000g")
        self.assertTrue(are_measurements_equal(m1, m2))

        m3 = extract_measurement("500g")
        self.assertFalse(are_measurements_equal(m1, m3))

    def test_strip_measurement(self):
        self.assertEqual(strip_measurement("1 kg salt"), "salt")
        self.assertEqual(strip_measurement("salt 1kg"), "salt")
        self.assertEqual(strip_measurement("Tata Salt 500g pack"), "Tata Salt")

    def test_analyze_measurement_matches_mismatch(self):
        # Requested 1 kg salt, but search results only have 300g, 500g, 2 kg
        candidates = [
            "Tata Salt 500g Pouch MRP Rs 15",
            "Tata Salt 2kg Family Pack MRP Rs 50",
            "Aashirvaad Salt 300g Table Shaker MRP Rs 25",
        ]
        analysis = analyze_measurement_matches("1 kg salt", candidates)
        self.assertTrue(analysis["has_requested_measurement"])
        self.assertEqual(analysis["requested_measurement"], "1 kg")
        self.assertFalse(analysis["exact_found"])
        self.assertEqual(analysis["status"], "measurement_mismatch")
        self.assertEqual(analysis["other_measurements"], ["300 g", "500 g", "2 kg"])

    def test_analyze_measurement_matches_exact(self):
        candidates = [
            "Tata Salt 500g Pouch MRP Rs 15",
            "Tata Salt 1kg Pack MRP Rs 28",
        ]
        analysis = analyze_measurement_matches("1 kg salt", candidates)
        self.assertTrue(analysis["exact_found"])
        self.assertEqual(analysis["status"], "exact_matched")


if __name__ == "__main__":
    unittest.main()

