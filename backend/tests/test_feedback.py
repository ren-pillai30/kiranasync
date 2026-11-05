import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app import main


class FeedbackRouteTests(unittest.TestCase):
    def setUp(self):
        self.previous_testing = main.app.config.get("TESTING", False)
        main.app.config["TESTING"] = True
        self.client = main.app.test_client()

    def tearDown(self):
        main.app.config["TESTING"] = self.previous_testing

    def test_feedback_requires_an_authenticated_account(self):
        with patch(
            "backend.app.main.current_user",
            SimpleNamespace(is_authenticated=False),
        ):
            response = self.client.post(
                "/api/feedback",
                json={"rating": 5, "category": "General", "message": "Helpful"},
            )

        self.assertEqual(response.status_code, 401)

    def test_feedback_is_emailed_with_server_authenticated_account_details(self):
        user = SimpleNamespace(
            is_authenticated=True,
            email="owner@example.com",
            display_name="Store Owner",
            store=SimpleNamespace(name="Corner Shop"),
        )
        provider_response = SimpleNamespace(ok=True, status_code=200)
        config = {
            "FEEDBACK_RESEND_API_KEY": "test-key",
            "FEEDBACK_FROM_EMAIL": "feedback@example.com",
            "FEEDBACK_TO_EMAIL": "developers@example.com",
        }

        with (
            patch.dict(os.environ, config),
            patch("backend.app.main.current_user", user),
            patch(
                "backend.app.main.requests.post",
                return_value=provider_response,
            ) as send_email,
        ):
            response = self.client.post(
                "/api/feedback",
                json={
                    "rating": 4,
                    "category": "Feature Request",
                    "message": "Please add weekly reports.",
                    "author": "Untrusted submitted name",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "success")
        send_email.assert_called_once()
        args, kwargs = send_email.call_args
        self.assertEqual(args[0], "https://api.resend.com/emails")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(kwargs["json"]["to"], ["developers@example.com"])
        self.assertIn("owner@example.com", kwargs["json"]["text"])
        self.assertIn("Corner Shop", kwargs["json"]["text"])
        self.assertIn("Please add weekly reports.", kwargs["json"]["text"])
        self.assertNotIn("Untrusted submitted name", kwargs["json"]["text"])

    def test_feedback_history_endpoint_is_not_available(self):
        response = self.client.get("/api/feedback")
        self.assertEqual(response.status_code, 404)

    def test_feedback_is_not_reported_as_sent_when_resend_fails(self):
        user = SimpleNamespace(
            is_authenticated=True,
            email="owner@example.com",
            display_name="Store Owner",
            store=SimpleNamespace(name="Corner Shop"),
        )
        provider_response = SimpleNamespace(ok=False, status_code=401)
        config = {
            "FEEDBACK_RESEND_API_KEY": "test-key",
            "FEEDBACK_FROM_EMAIL": "feedback@example.com",
            "FEEDBACK_TO_EMAIL": "developers@example.com",
        }

        with (
            patch.dict(os.environ, config),
            patch("backend.app.main.current_user", user),
            patch("backend.app.main.requests.post", return_value=provider_response),
        ):
            response = self.client.post(
                "/api/feedback",
                json={"rating": 5, "category": "General", "message": "Helpful"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["status"], "error")

    def test_feedback_validates_rating_and_category(self):
        user = SimpleNamespace(
            is_authenticated=True,
            email="owner@example.com",
            display_name="Store Owner",
            store=SimpleNamespace(name="Corner Shop"),
        )
        with patch("backend.app.main.current_user", user):
            invalid_rating = self.client.post(
                "/api/feedback",
                json={"rating": 6, "category": "General", "message": "Helpful"},
            )
            invalid_category = self.client.post(
                "/api/feedback",
                json={"rating": 5, "category": "Other", "message": "Helpful"},
            )

        self.assertEqual(invalid_rating.status_code, 400)
        self.assertEqual(invalid_category.status_code, 400)


if __name__ == "__main__":
    unittest.main()
