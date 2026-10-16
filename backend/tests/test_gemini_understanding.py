import os
import unittest
from unittest.mock import patch

from backend.app.gemini_understanding import (
    GeminiUnderstandingError,
    understand_command,
)


class GeminiUnderstandingTests(unittest.TestCase):
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("backend.app.gemini_understanding.requests.post")
    def test_returns_validated_command(self, post):
        response = post.return_value
        response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"action":"restock","entity":"Sugar 1kg",'
                                    '"quantity":"2000"}'
                                )
                            }
                        ]
                    }
                }
            ]
        }

        result = understand_command(
            transcript="do hazaar kg shakkar aayi hai",
            hindi_transcript=None,
            inventory=["Sugar 1kg"],
            customers=[],
        )

        self.assertEqual(
            result,
            {"action": "restock", "entity": "Sugar 1kg", "quantity": 2000},
        )
        self.assertIn("gemini-3.5-flash-lite:generateContent", post.call_args.args[0])
        self.assertEqual(
            post.call_args.kwargs["headers"]["x-goog-api-key"],
            "test-key",
        )

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("backend.app.gemini_understanding.requests.post")
    def test_rejects_non_integer_quantity(self, post):
        post.return_value.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"action":"sell","entity":"Sugar 1kg",'
                                    '"quantity":"1.5"}'
                                )
                            }
                        ]
                    }
                }
            ]
        }

        with self.assertRaisesRegex(
            GeminiUnderstandingError,
            "not a whole number",
        ):
            understand_command("sell sugar", None, ["Sugar 1kg"], [])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("backend.app.gemini_understanding.time.sleep")
    @patch("backend.app.gemini_understanding.requests.post")
    def test_retries_transient_service_unavailable(self, post, sleep):
        unavailable = post.return_value
        unavailable.status_code = 503
        success = unittest.mock.MagicMock()
        success.status_code = 200
        success.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"action":"sell","entity":"Sugar 1kg",'
                                    '"quantity":"1"}'
                                )
                            }
                        ]
                    }
                }
            ]
        }
        post.side_effect = [unavailable, success]

        result = understand_command("sugar bhej do", None, ["Sugar 1kg"], [])

        self.assertEqual(
            result,
            {"action": "sell", "entity": "Sugar 1kg", "quantity": 1},
        )
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(0.5)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("backend.app.gemini_understanding.time.sleep")
    @patch("backend.app.gemini_understanding.requests.post")
    def test_reports_service_unavailable_after_retry_limit(self, post, sleep):
        post.return_value.status_code = 503

        with self.assertRaisesRegex(
            GeminiUnderstandingError,
            "temporarily unavailable \\(503\\)",
        ):
            understand_command("sugar bhej do", None, ["Sugar 1kg"], [])

        self.assertEqual(post.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch.dict(os.environ, {}, clear=True)
    @patch("backend.app.gemini_understanding.requests.post")
    def test_requires_api_key(self, post):
        with self.assertRaisesRegex(GeminiUnderstandingError, "GEMINI_API_KEY"):
            understand_command("sell sugar", None, ["Sugar 1kg"], [])

        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
