import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import ANY, patch

from backend.app import main
from backend.app import intent_parser
from backend.app.gemini_understanding import GeminiUnderstandingError


class ProcessAudioRouteTests(unittest.TestCase):
    def setUp(self):
        self.previous_testing = main.app.config.get("TESTING", False)
        main.app.config["TESTING"] = True
        self.database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database_path = self.database_file.name
        self.database_file.close()
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE Inventory (
                    ItemID INTEGER PRIMARY KEY,
                    ItemName TEXT,
                    ItemNameHindi TEXT,
                    IsActive INTEGER DEFAULT 1
                );
                CREATE TABLE CustomerCredit (
                    CustomerID INTEGER PRIMARY KEY,
                    CustomerName TEXT,
                    CustomerNameHindi TEXT,
                    IsActive INTEGER DEFAULT 1
                );
                """
            )
        self.database_patch = patch.object(intent_parser, "DB_PATH", self.database_path)
        self.database_patch.start()

    def tearDown(self):
        self.database_patch.stop()
        main.app.config["TESTING"] = self.previous_testing
        if os.path.exists(self.database_path):
            os.remove(self.database_path)

    @patch.dict(
        os.environ,
        {"GNANI_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"},
    )
    @patch("backend.app.services.query_service.QueryService")
    @patch("backend.app.main.parse_and_execute")
    @patch("backend.app.main.understand_command")
    @patch("backend.app.main.transcribe_audio", return_value="मैगी बेच दीजिए")
    def test_hindi_voice_command_does_not_repeat_hindi_transcription(
        self,
        transcribe_audio,
        understand_command,
        parse_and_execute,
        query_service,
    ):
        understand_command.return_value = {
            "action": "sell",
            "entity": "Maggi 70g",
            "quantity": 2,
            "spoken_response": "क्या मैं आगे बढ़ूँ?",
        }
        parse_and_execute.return_value = {
            "status": "pending_confirmation",
            "action": "confirm_sale",
            "message": "Confirm sale",
        }
        query_service.return_value.get_store_kpis.return_value = {}

        response = main.app.test_client().post(
            "/api/process-audio",
            data={
                "audio": (io.BytesIO(b"audio"), "command.wav"),
                "lang": "hi-IN",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transcribe_audio.call_count, 1)
        transcribe_audio.assert_called_once_with(
            ANY,
            language_code="hi-IN",
        )
        understand_command.assert_called_once()
        parse_and_execute.assert_called_once()

    @patch.dict(
        os.environ,
        {"GNANI_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"},
    )
    @patch("backend.app.services.query_service.QueryService")
    @patch(
        "backend.app.main.parse_and_execute",
        side_effect=GeminiUnderstandingError(
            "Gemini's API quota or rate limit was reached (429)."
        ),
    )
    @patch("backend.app.main.understand_command")
    @patch("backend.app.main.transcribe_audio", return_value="मैगी बेच दीजिए")
    def test_voice_route_surfaces_gemini_catalog_matching_errors(
        self,
        transcribe_audio,
        understand_command,
        parse_and_execute,
        query_service,
    ):
        understand_command.return_value = {
            "action": "sell",
            "entity": "मैगी",
            "quantity": 2,
        }
        query_service.return_value.get_store_kpis.return_value = {}

        response = main.app.test_client().post(
            "/api/process-audio",
            data={
                "audio": (io.BytesIO(b"audio"), "command.wav"),
                "lang": "hi-IN",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("quota or rate limit", response.get_json()["error"])
        parse_and_execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
