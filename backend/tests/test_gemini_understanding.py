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
                                    '"quantity":"2000","transcript_index":0}'
                                )
                            }
                        ]
                    }
                }
            ]
        }

        result = understand_command(
            transcripts=[{
                "language_code": "hi-IN",
                "transcript": "do hazaar kg shakkar aayi hai",
            }],
            inventory=["Sugar 1kg"],
            customers=[],
        )

        self.assertEqual(
            result,
            {
                "action": "restock",
                "entity": "Sugar 1kg",
                "quantity": 2000,
                "transcript_index": 0,
            },
        )
        self.assertIn("gemini-3.5-flash-lite:generateContent", post.call_args.args[0])
        self.assertEqual(
            post.call_args.kwargs["headers"]["x-goog-api-key"],
            "test-key",
        )

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("backend.app.gemini_understanding.requests.post")
    def test_uses_all_transcripts_to_resolve_code_switched_number(self, post):
        post.return_value.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"action":"restock","entity":"Sugar 1kg",'
                                    '"quantity":"64","transcript_index":0}'
                                )
                            }
                        ]
                    }
                }
            ]
        }
        transcripts = [
            {
                "language_code": "en-IN",
                "transcript": "Add chaunsath kg of sugar",
            },
            {
                "language_code": "te-IN",
                "transcript": "add 4 kg of sugar",
            },
            {
                "language_code": "hi-IN",
                "transcript": "चौंसठ किलो चीनी",
            },
        ]

        result = understand_command(transcripts, ["Sugar 1kg"], [])

        self.assertEqual(
            result,
            {
                "action": "restock",
                "entity": "Sugar 1kg",
                "quantity": 64,
                "transcript_index": 0,
            },
        )
        prompt = post.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]
        self.assertIn("Compare all candidates semantically and phonetically", prompt)
        self.assertIn("written phonetically in Latin script", prompt)
        self.assertIn("recover the complete spoken number", prompt.lower())
        self.assertIn("Add chaunsath kg of sugar", prompt)
        self.assertIn("add 4 kg of sugar", prompt)

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
                                    '"quantity":"1.5","transcript_index":0}'
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
            understand_command(
                [{"language_code": "en-IN", "transcript": "sell sugar"}],
                ["Sugar 1kg"],
                [],
            )

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("backend.app.gemini_understanding.requests.post")
    def test_rejects_transcript_index_outside_candidate_list(self, post):
        post.return_value.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"action":"sell","entity":"Sugar 1kg",'
                                    '"quantity":"1","transcript_index":1}'
                                )
                            }
                        ]
                    }
                }
            ]
        }

        with self.assertRaisesRegex(
            GeminiUnderstandingError,
            "invalid format",
        ):
            understand_command(
                [{"language_code": "en-IN", "transcript": "sell sugar"}],
                ["Sugar 1kg"],
                [],
            )

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
                                    '"quantity":"1","transcript_index":0}'
                                )
                            }
                        ]
                    }
                }
            ]
        }
        post.side_effect = [unavailable, success]

        result = understand_command(
            [{"language_code": "hi-IN", "transcript": "sugar bhej do"}],
            ["Sugar 1kg"],
            [],
        )

        self.assertEqual(
            result,
            {
                "action": "sell",
                "entity": "Sugar 1kg",
                "quantity": 1,
                "transcript_index": 0,
            },
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
            understand_command(
                [{"language_code": "hi-IN", "transcript": "sugar bhej do"}],
                ["Sugar 1kg"],
                [],
            )

        self.assertEqual(post.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch.dict(os.environ, {}, clear=True)
    @patch("backend.app.gemini_understanding.requests.post")
    def test_requires_api_key(self, post):
        with self.assertRaisesRegex(GeminiUnderstandingError, "GEMINI_API_KEY"):
            understand_command(
                [{"language_code": "en-IN", "transcript": "sell sugar"}],
                ["Sugar 1kg"],
                [],
            )

        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
