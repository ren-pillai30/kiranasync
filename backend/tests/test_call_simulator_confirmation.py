import io
import json
import unittest
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.main import app
from backend.app.routers import call_router
from backend.app.services.call_db_service import CallDBService


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

    def test_postgres_call_context_uses_current_store_inventory(self):
        from backend.app.models import StoreCredit, StoreInventory

        with app.app_context(), patch(
            "backend.app.services.call_db_service.is_postgres_database",
            return_value=True,
        ), patch("backend.app.models.StoreInventory.query") as inventory_query, patch(
            "backend.app.models.StoreCredit.query"
        ) as customer_query:
            inventory_query.filter_by.return_value.order_by.return_value.all.return_value = [
                SimpleNamespace(
                    item_id=3,
                    item_name="Chocos (MRP ₹10)",
                    item_name_hindi="चोकोस",
                    stock_quantity=80,
                    price=10,
                )
            ]
            customer_query.filter_by.return_value.order_by.return_value.all.return_value = []
            service = CallDBService(store_id=42)
            context = service.get_store_context()

        self.assertEqual(context["inventory"][0]["ItemName"], "Chocos (MRP ₹10)")
        self.assertEqual(context["inventory"][0]["ItemNameHindi"], "चोकोस")
        self.assertEqual(context["inventory"][0]["StockQuantity"], 80)
        inventory_query.filter_by.assert_called_once_with(store_id=42, is_active=True)

    def test_postgres_confirmed_call_order_writes_to_current_store(self):
        from backend.app.database import db
        from backend.app.models import StoreInventory

        with app.app_context():
            service = CallDBService(store_id=42)
            service.use_postgres = True
            inventory_item = SimpleNamespace(
                item_id=3,
                item_name="Chocos (MRP ₹10)",
                stock_quantity=80,
            )
            with patch.object(
                service,
                "match_inventory_item",
                return_value={
                    "ItemID": 3,
                    "ItemName": "Chocos (MRP ₹10)",
                    "StockQuantity": 80,
                    "Price": 10,
                },
            ), patch.object(
                service, "_record_postgres_transaction"
            ) as record_transaction, patch.object(
                db.session, "commit"
            ) as commit, patch.object(
                db.session, "rollback"
            ) as rollback, patch(
                "backend.app.models.StoreInventory.query"
            ) as inventory_query:
                inventory_query.filter_by.return_value.with_for_update.return_value.first.return_value = inventory_item
                result = service.execute_order(
                    [{"name": "Chocos", "quantity": 10}],
                    raw_call_text="Call order: 10 packets Chocos",
                )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["items"][0]["item_name"], "Chocos (MRP ₹10)")
        self.assertEqual(inventory_item.stock_quantity, 70)
        inventory_query.filter_by.assert_called_once_with(
            store_id=42,
            item_id=3,
            is_active=True,
        )
        record_transaction.assert_called_once()
        commit.assert_called_once()
        rollback.assert_not_called()

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

        with patch("backend.app.main.current_store_id", return_value=42):
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
                self.assertEqual(pending["audio_base64"], "YXVkaW8=")
                self.assertEqual(pending["audio_content_type"], "audio/wav")
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
        self.assertEqual(
            [call_args.kwargs for call_args in db_class.call_args_list],
            [{"store_id": 42}, {"store_id": 42}],
        )

    @patch("backend.app.services.gnani_service.GnaniService")
    @patch("backend.app.services.call_db_service.CallDBService")
    @patch("backend.app.services.call_gemini_service.CallGeminiService")
    def test_http_inventory_inquiry_falls_back_when_gemini_fails(
        self,
        gemini_class,
        db_class,
        gnani_class,
    ):
        gemini_class.return_value.process_call_turn.return_value = {
            "reply_text": "",
            "action_type": "service_error",
            "action_data": {},
            "detected_language_code": "hi-IN",
            "error": "Gemini intent parsing failed.",
        }
        db = db_class.return_value
        db.get_store_context.return_value = {
            "inventory": [{
                "ItemName": "Maggi",
                "ItemNameHindi": "मैगी",
                "StockQuantity": 10,
                "Price": 14,
            }],
            "customers": [],
        }
        db.answer_inventory_inquiry.return_value = (
            "Gemini अभी उपलब्ध नहीं है। मैगी का स्टॉक 10 है और कीमत ₹14 है।"
        )
        gnani_class.return_value.synthesize_speech.return_value = (
            b"spoken reply",
            "audio/wav",
        )

        response = app.test_client().post(
            "/api/call/http/turn",
            json={
                "user_input": "Maggi ka kitna stock hai aur price kya hai?",
                "caller_name": "Ramesh",
                "language_code": "hi-IN",
                "conversation_history": [],
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action_type"], "inventory_inquiry")
        self.assertIsNone(result["error"])
        self.assertEqual(result["audio_base64"], "c3Bva2VuIHJlcGx5")
        self.assertFalse(result["audio_error"])
        db.answer_inventory_inquiry.assert_called_once_with(
            "Maggi ka kitna stock hai aur price kya hai?",
            db.get_store_context.return_value["inventory"],
            language_code="hi-IN",
        )
        db.execute_action.assert_not_called()

    @patch("backend.app.services.gnani_service.GnaniService")
    @patch("backend.app.services.call_db_service.CallDBService")
    @patch("backend.app.services.call_gemini_service.CallGeminiService")
    def test_http_gemini_and_tts_failures_are_reported(
        self,
        gemini_class,
        db_class,
        gnani_class,
    ):
        gemini_class.return_value.process_call_turn.return_value = {
            "reply_text": "",
            "action_type": "service_error",
            "action_data": {},
            "detected_language_code": "en-IN",
            "error": "Gemini intent parsing failed.",
        }
        db = db_class.return_value
        db.get_store_context.return_value = {"inventory": [], "customers": []}
        db.answer_inventory_inquiry.return_value = None
        gnani_class.return_value.synthesize_speech.return_value = (None, "audio/wav")

        response = app.test_client().post(
            "/api/call/http/turn",
            json={
                "user_input": "Please add this to Ramesh's credit",
                "caller_name": "Ramesh",
                "language_code": "en-IN",
                "conversation_history": [],
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["action_type"], "service_error")
        self.assertIn("Gemini", result["reply_text"])
        self.assertIsNone(result["audio_base64"])
        self.assertIn("Gnani", result["audio_error"])
        db.execute_action.assert_not_called()

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
