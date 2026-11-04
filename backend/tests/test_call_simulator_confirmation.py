import io
import json
import unittest
import asyncio
from unittest.mock import patch

from backend.app.main import app
from backend.app.routers import call_router


class CallSimulatorConfirmationRouteTests(unittest.TestCase):
    def setUp(self):
        self.previous_testing = app.config.get("TESTING", False)
        self.previous_login_disabled = app.config.get("LOGIN_DISABLED", False)
        app.config.update(TESTING=True, LOGIN_DISABLED=True)

    def tearDown(self):
        app.config.update(
            TESTING=self.previous_testing,
            LOGIN_DISABLED=self.previous_login_disabled,
        )

    @patch("backend.app.services.gnani_service.GnaniService")
    @patch("backend.app.services.call_db_service.CallDBService")
    @patch("backend.app.services.call_gemini_service.CallGeminiService")
    def test_http_call_requires_confirmation_before_database_write(
        self,
        gemini_class,
        db_class,
        gnani_class,
    ):
        gemini = gemini_class.return_value
        gemini.process_call_turn.return_value = {
            "reply_text": "Would you like me to proceed?",
            "action_type": "order",
            "action_data": {"items": [{"name": "Maggi", "quantity": 2}]},
            "detected_language_code": "en-IN",
        }
        gemini.generate_action_confirmation.return_value = (
            "Should I record two Maggi packets?"
        )
        gemini.classify_confirmation.return_value = "confirmed"
        gemini.generate_action_result.return_value = "Your order is recorded."
        db = db_class.return_value
        db.get_store_context.return_value = {"inventory": [], "customers": []}
        db.execute_action.return_value = {
            "status": "success",
            "action": "order_placed",
            "message": "Order recorded.",
            "items": [{
                "item_name": "Maggi",
                "quantity": 2,
                "unit_price": 14,
                "item_total": 28,
            }],
        }
        gnani_class.return_value.synthesize_speech.return_value = (b"audio", "audio/wav")

        with app.test_client() as client:
            response = client.post(
                "/api/call/turn",
                json={
                    "user_input": "Sell two Maggi",
                    "caller_name": "Ramesh",
                    "language_code": "en-IN",
                    "conversation_history": [],
                },
            )
            self.assertEqual(response.status_code, 200)
            pending = response.get_json()
            self.assertTrue(pending["confirmation_required"])
            self.assertEqual(pending["transcript_text"], "Sell two Maggi")
            db.execute_action.assert_not_called()

            confirmation = client.post(
                "/api/call/turn",
                json={
                    "user_input": "Yes, go ahead",
                    "caller_name": "Ramesh",
                    "language_code": "en-IN",
                    "conversation_history": [],
                },
            )

        self.assertEqual(confirmation.status_code, 200)
        completed = confirmation.get_json()
        self.assertFalse(completed["confirmation_required"])
        self.assertEqual(completed["db_result"]["status"], "success")
        db.execute_action.assert_called_once()

    @patch("backend.app.services.gnani_service.GnaniService")
    @patch("backend.app.services.call_db_service.CallDBService")
    @patch("backend.app.services.call_gemini_service.CallGeminiService")
    def test_audio_turn_uses_gnani_transcription(
        self,
        gemini_class,
        db_class,
        gnani_class,
    ):
        gemini = gemini_class.return_value
        gemini.process_call_turn.return_value = {
            "reply_text": "How can I help?",
            "action_type": "general",
            "action_data": {},
            "detected_language_code": "hi-IN",
        }
        db_class.return_value.get_store_context.return_value = {
            "inventory": [],
            "customers": [],
        }
        gnani = gnani_class.return_value
        gnani.transcribe_audio_bytes.return_value = "Namaste"
        gnani.synthesize_speech.return_value = (b"audio", "audio/wav")

        response = app.test_client().post(
            "/api/call/turn",
            data={
                "audio": (io.BytesIO(b"wav-data"), "call-audio.wav"),
                "caller_name": "Ramesh",
                "language_code": "hi-IN",
                "conversation_history": json.dumps([]),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["transcript_text"], "Namaste")
        gnani.transcribe_audio_bytes.assert_called_once_with(
            b"wav-data",
            language_code="hi-IN",
        )

    @patch.object(call_router, "gnani_service")
    @patch.object(call_router, "db_service")
    @patch.object(call_router, "gemini_service")
    def test_websocket_call_executes_only_after_confirmation(
        self,
        gemini,
        db,
        gnani,
    ):
        class MockWebSocket:
            def __init__(self):
                self.incoming = [
                    {"type": "start_call", "customer_name": "Ramesh", "language_code": "en-IN"},
                    {"type": "text_input", "text": "Sell two Maggi"},
                    {"type": "text_input", "text": "Yes, go ahead"},
                    {"type": "end_call"},
                ]
                self.sent = []

            async def accept(self):
                return None

            async def receive(self):
                if not self.incoming:
                    return {"type": "websocket.disconnect"}
                return {
                    "type": "websocket.receive",
                    "text": json.dumps(self.incoming.pop(0)),
                }

            async def send_json(self, data):
                self.sent.append(data)

        gemini.generate_call_greeting.return_value = "Welcome."
        gemini.process_call_turn.return_value = {
            "reply_text": "Would you like me to proceed?",
            "action_type": "order",
            "action_data": {"items": [{"name": "Maggi", "quantity": 2}]},
            "detected_language_code": "en-IN",
        }
        gemini.generate_action_confirmation.return_value = "Confirm two Maggi?"
        gemini.classify_confirmation.return_value = "confirmed"
        gemini.generate_action_result.return_value = "Your order is recorded."
        db.get_store_context.return_value = {"inventory": [], "customers": []}
        db.execute_action.return_value = {
            "status": "success",
            "action": "order_placed",
            "message": "Order recorded.",
            "items": [],
        }
        gnani.synthesize_speech_base64.return_value = None

        websocket = MockWebSocket()
        asyncio.run(call_router.call_websocket_endpoint(websocket))

        responses = [message for message in websocket.sent if message["type"] == "call_response"]
        self.assertEqual(len(responses), 2)
        self.assertTrue(responses[0]["confirmation_required"])
        self.assertIsNone(responses[0]["db_result"])
        self.assertFalse(responses[1]["confirmation_required"])
        self.assertEqual(responses[1]["db_result"]["status"], "success")
        db.execute_action.assert_called_once()


if __name__ == "__main__":
    unittest.main()
