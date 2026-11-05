import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from backend.app import main
from backend.app.models import StoreTransaction


class HisaabAnalyticsTests(unittest.TestCase):
    def test_postgres_hisaab_uses_store_transactions_and_active_customer_balances(self):
        transaction_query = MagicMock()
        transaction_query.filter.return_value.group_by.return_value.all.return_value = [
            ("Sale", 80, 2),
            ("UdhaarSale", 40, 1),
            ("Repayment", 20, 1),
            ("Restock", -12, 1),
            ("Credit", 100, 1),
        ]
        debt_query = MagicMock()
        debt_query.filter_by.return_value.scalar.return_value = 120

        with (
            main.app.app_context(),
            main.app.test_client() as client,
            patch.dict(main.app.config, {"TESTING": True}),
            patch("backend.app.main.is_postgres_database", return_value=True),
            patch("backend.app.main.current_store_id", return_value=7),
            patch(
                "backend.app.main.current_user",
                SimpleNamespace(
                    is_authenticated=True,
                    store=SimpleNamespace(register_opening_balance=50),
                ),
            ),
            patch(
                "backend.app.main.db.session.query",
                side_effect=[transaction_query, debt_query],
            ) as query,
        ):
            response = client.get("/api/analytics/hisaab")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "status": "success",
                "CashSalesTotal": 80,
                "CashSalesCount": 2,
                "UdhaarSalesTotal": 40,
                "UdhaarSalesCount": 1,
                "RepaymentsTotal": 20,
                "RepaymentsCount": 1,
                "RestockCostTotal": 12,
                "TotalRevenue": 120,
                "CashCollected": 150,
                "TotalOutstandingDebt": 120,
                "Message": (
                    "Today's Hisaab: Total Sales ₹120 (Cash: ₹80, Udhaar: ₹40). "
                    "Cash in register: ₹150. Total customer debt: ₹120."
                ),
            },
        )
        transaction_query.filter.assert_called_once()
        filter_args = transaction_query.filter.call_args.args
        self.assertEqual(len(filter_args), 3)
        self.assertEqual(
            str(filter_args[0]),
            str(StoreTransaction.store_id == 7),
        )
        debt_query.filter_by.assert_called_once_with(store_id=7, is_active=True)
        self.assertEqual(query.call_count, 2)

    def test_sqlite_hisaab_adds_store_opening_register_balance(self):
        stored_hisaab = {
            "status": "success",
            "CashSalesTotal": 80,
            "UdhaarSalesTotal": 40,
            "RepaymentsTotal": 20,
            "TotalRevenue": 120,
            "CashCollected": 100,
            "TotalOutstandingDebt": 120,
            "Message": "",
        }
        with (
            main.app.app_context(),
            main.app.test_client() as client,
            patch.dict(main.app.config, {"TESTING": True}),
            patch("backend.app.main.is_postgres_database", return_value=False),
            patch(
                "backend.app.main.current_user",
                SimpleNamespace(
                    is_authenticated=True,
                    store=SimpleNamespace(register_opening_balance=50),
                ),
            ),
            patch(
                "backend.app.services.query_service.QueryService.get_today_hisaab",
                return_value=stored_hisaab.copy(),
            ),
        ):
            response = client.get("/api/analytics/hisaab")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["CashCollected"], 150)
        self.assertIn("Cash in register: ₹150", response.get_json()["Message"])


if __name__ == "__main__":
    unittest.main()
