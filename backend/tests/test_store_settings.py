import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app import main


class StoreSettingsTests(unittest.TestCase):
    def setUp(self):
        self.previous_testing = main.app.config.get("TESTING", False)
        main.app.config["TESTING"] = True
        self.client = main.app.test_client()
        self.store = SimpleNamespace(
            name="Old Shop",
            phone="111",
            address="Old Road",
            city="Old City",
            register_opening_balance=0,
            setup_complete=False,
        )
        self.user = SimpleNamespace(is_authenticated=True, store=self.store)

    def tearDown(self):
        main.app.config["TESTING"] = self.previous_testing

    def test_setup_saves_register_opening_balance_for_the_store(self):
        with (
            patch("backend.app.auth.current_user", self.user),
            patch("backend.app.auth.db.session.commit") as commit,
        ):
            response = self.client.post(
                "/api/store/setup",
                json={
                    "store_name": "Corner Shop",
                    "phone": "222",
                    "address": "New Road",
                    "city": "New City",
                    "register_opening_balance": 1250.50,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.store.register_opening_balance, 1250.50)
        self.assertTrue(self.store.setup_complete)
        self.assertEqual(
            response.get_json()["store"]["register_opening_balance"],
            1250.50,
        )
        commit.assert_called_once()

    def test_setup_rejects_negative_register_opening_balance(self):
        with patch("backend.app.auth.current_user", self.user):
            response = self.client.post(
                "/api/store/setup",
                json={
                    "store_name": "Corner Shop",
                    "phone": "222",
                    "address": "New Road",
                    "city": "New City",
                    "register_opening_balance": -1,
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.store.register_opening_balance, 0)


if __name__ == "__main__":
    unittest.main()
