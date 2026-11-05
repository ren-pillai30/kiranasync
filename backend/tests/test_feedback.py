import base64
import io
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
            "FEEDBACK_BREVO_API_KEY": "test-key",
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
        self.assertEqual(args[0], "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertEqual(kwargs["headers"]["api-key"], "test-key")
        self.assertEqual(kwargs["json"]["to"], [{"email": "developers@example.com"}])
        self.assertIn("owner@example.com", kwargs["json"]["textContent"])
        self.assertIn("Corner Shop", kwargs["json"]["textContent"])
        self.assertIn("Please add weekly reports.", kwargs["json"]["textContent"])
        self.assertNotIn("Untrusted submitted name", kwargs["json"]["textContent"])
        self.assertEqual(
            kwargs["json"]["sender"]["email"],
            "feedback@example.com",
        )

    def test_feedback_emails_uploaded_image_as_private_attachment(self):
        user = SimpleNamespace(
            is_authenticated=True,
            email="owner@example.com",
            display_name="Store Owner",
            store=SimpleNamespace(name="Corner Shop"),
        )
        image_bytes = b"\xff\xd8\xfftest image bytes"
        provider_response = SimpleNamespace(ok=True, status_code=200)
        config = {
            "FEEDBACK_BREVO_API_KEY": "test-key",
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
                data={
                    "rating": "5",
                    "category": "Bug Report",
                    "message": "The page is blank.",
                    "images": (io.BytesIO(image_bytes), "screen shot.jpg", "image/jpeg"),
                },
            )

        self.assertEqual(response.status_code, 200)
        attachment = send_email.call_args.kwargs["json"]["attachment"]
        self.assertEqual(attachment, [{
            "name": "screen_shot.jpg",
            "content": base64.b64encode(image_bytes).decode("ascii"),
        }])
        self.assertIn("screen_shot.jpg", send_email.call_args.kwargs["json"]["textContent"])

    def test_feedback_rejects_non_image_upload(self):
        user = SimpleNamespace(
            is_authenticated=True,
            email="owner@example.com",
            display_name="Store Owner",
            store=SimpleNamespace(name="Corner Shop"),
        )
        with (
            patch("backend.app.main.current_user", user),
            patch("backend.app.main.requests.post") as send_email,
        ):
            response = self.client.post(
                "/api/feedback",
                data={
                    "rating": "5",
                    "category": "Bug Report",
                    "message": "The page is blank.",
                    "images": (io.BytesIO(b"not an image"), "screenshot.jpg", "image/jpeg"),
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("not a valid JPEG image", response.get_json()["error"])
        send_email.assert_not_called()

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
            "FEEDBACK_BREVO_API_KEY": "test-key",
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
