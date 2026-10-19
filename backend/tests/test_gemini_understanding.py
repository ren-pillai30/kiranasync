import os
import unittest
from unittest.mock import patch

from backend.app.gemini_understanding import (
    GeminiUnderstandingError,
    translate_for_speech,
    understand_command,
)


class GeminiUnderstandingTests(unittest.TestCase):
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("backend.app.gemini_understanding.requests.post")
    def test_translates_spoken_response_to_selected_language(self, post):
        response = post.return_value
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": '{"translation":"चीनी के 5 पैकेट बचे हैं।"}'}]
                }
            }]
        }

        translation = translate_for_speech("Sugar: 5 in stock.", "hi-IN")

        self.assertEqual(translation, "चीनी के 5 पैकेट बचे हैं।")
        request_text = post.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]
        self.assertIn("hi-IN", request_text)
        self.assertIn("Sugar: 5 in stock.", request_text)

    @patch("backend.app.gemini_understanding.requests.post")
    def test_does_not_translate_english_response(self, post):
        self.assertEqual(
            translate_for_speech("Sugar: 5 in stock.", "en-IN"),
            "Sugar: 5 in stock.",
        )
        post.assert_not_called()

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
    @patch("backend.app.gemini_understanding.requests.post")
    def test_validates_gemini_removal_intent_and_reason(self, post):
        post.return_value.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"action":"remove_product","entity":"Milk 1L",'
                                    '"quantity":"","reason":"recalled"}'
                                )
                            }
                        ]
                    }
                }
            ]
        }

        result = understand_command(
            "remove the recalled milk",
            inventory=["Milk 1L"],
            customers=[],
        )

        self.assertEqual(
            result,
            {
                "action": "remove_product",
                "entity": "Milk 1L",
                "quantity": None,
                "reason": "recalled",
            },
        )
        schema = post.call_args.kwargs["json"]["generationConfig"]["responseSchema"]
        self.assertIn("remove_product", schema["properties"]["action"]["enum"])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("backend.app.gemini_understanding.requests.post")
    def test_prompt_distinguishes_new_customer_credit_from_repayment(self, post):
        post.return_value.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": (
                            '{"action":"credit","entity":"श्याम",'
                            '"quantity":"1564"}'
                        )
                    }]
                }
            }]
        }

        result = understand_command(
            "श्याम के खाते में 1564 डाल दो",
            inventory=[],
            customers=[],
        )

        prompt = post.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]
        self.assertEqual(result["action"], "credit")
        self.assertIn("create their customer row with that balance", prompt)
        self.assertIn("Only choose repayment when the customer is clearly paying", prompt)

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
