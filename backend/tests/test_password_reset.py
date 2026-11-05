import os
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

from backend.app import main
from backend.app.auth import _password_reset_serializer, _password_reset_verifier
from backend.app.models import User


class PasswordResetTests(unittest.TestCase):
    def setUp(self):
        self.user = User(
            id=42,
            email="owner@example.com",
            display_name="Store Owner",
            password_hash="",
            is_active=True,
        )
        self.user.set_password("old-password-123")
        self.client = main.app.test_client()

    def test_request_sends_short_lived_reset_link_through_brevo(self):
        query_result = MagicMock()
        query_result.scalar_one_or_none.return_value = self.user
        response_from_provider = MagicMock(ok=True, status_code=201)
        with (
            main.app.app_context(),
            patch.dict(
                os.environ,
                {
                    "FEEDBACK_BREVO_API_KEY": "test-key",
                    "FEEDBACK_FROM_EMAIL": "verified@example.com",
                    "APP_BASE_URL": "https://shop.example.com/",
                },
            ),
            patch(
                "backend.app.auth.db.session.execute",
                return_value=query_result,
            ),
            patch(
                "backend.app.auth.requests.post",
                return_value=response_from_provider,
            ) as send_email,
        ):
            response = self.client.post(
                "/api/auth/password-reset/request",
                json={"email": "OWNER@example.com"},
            )
            token = parse_qs(
                urlsplit(
                    send_email.call_args.kwargs["json"]["htmlContent"]
                    .split('href="', 1)[1]
                    .split('"', 1)[0]
                ).fragment
            )["reset_token"][0]
            payload = _password_reset_serializer().loads(token, max_age=1800)
            expected_verifier = _password_reset_verifier(self.user)

        self.assertEqual(response.status_code, 200)
        send_email.assert_called_once()
        email = send_email.call_args.kwargs["json"]
        self.assertEqual(email["to"], [{"email": "owner@example.com"}])
        self.assertEqual(email["sender"]["email"], "verified@example.com")
        link = email["htmlContent"].split('href="', 1)[1].split('"', 1)[0]
        self.assertEqual(urlsplit(link).netloc, "shop.example.com")
        self.assertEqual(payload["user_id"], 42)
        self.assertEqual(payload["verifier"], expected_verifier)
        self.assertIn("expires in 30 minutes", email["htmlContent"])

    def test_reset_changes_password_and_invalidates_the_link(self):
        with (
            main.app.app_context(),
            patch("backend.app.auth.db.session.get", return_value=self.user),
            patch("backend.app.auth.db.session.commit") as commit,
        ):
            token = _password_reset_serializer().dumps({
                "user_id": self.user.id,
                "verifier": _password_reset_verifier(self.user),
            })
            response = self.client.post(
                "/api/auth/password-reset/confirm",
                json={"token": token, "password": "new-password-123"},
            )
            retry = self.client.post(
                "/api/auth/password-reset/confirm",
                json={"token": token, "password": "another-password-123"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.user.check_password("new-password-123"))
        self.assertEqual(retry.status_code, 400)
        commit.assert_called_once()

    def test_unknown_email_receives_same_response_without_sending_email(self):
        query_result = MagicMock()
        query_result.scalar_one_or_none.return_value = None
        with (
            main.app.app_context(),
            patch("backend.app.auth.db.session.execute", return_value=query_result),
            patch("backend.app.auth.requests.post") as send_email,
        ):
            response = self.client.post(
                "/api/auth/password-reset/request",
                json={"email": "unknown@example.com"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("If an account exists", response.get_json()["message"])
        send_email.assert_not_called()

    def test_invalid_token_and_weak_password_are_rejected(self):
        with (
            main.app.app_context(),
            patch("backend.app.auth.db.session.get", return_value=self.user),
            patch("backend.app.auth.db.session.commit") as commit,
        ):
            invalid_token = self.client.post(
                "/api/auth/password-reset/confirm",
                json={"token": "not-a-token", "password": "new-password-123"},
            )
            weak_password = self.client.post(
                "/api/auth/password-reset/confirm",
                json={"token": "not-a-token", "password": "short"},
            )

        self.assertEqual(invalid_token.status_code, 400)
        self.assertEqual(weak_password.status_code, 400)
        commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
