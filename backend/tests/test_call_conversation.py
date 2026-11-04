import unittest
from unittest.mock import Mock, patch

from backend.app.services.call_conversation import process_call_turn
from backend.app.services.call_gemini_service import CallGeminiService


class CallConversationConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.gemini = Mock()
        self.database = Mock()

    def process(self, utterance, pending_action=None):
        return process_call_turn(
            user_utterance=utterance,
            conversation_history=[],
            inventory_items=[],
            customers=[],
            caller_name="Ramesh",
            language_code="en-IN",
            gemini_service=self.gemini,
            db_service=self.database,
            pending_action=pending_action,
            raw_call_text="Call: test",
        )

    def test_mutation_is_held_until_confirmation(self):
        self.gemini.process_call_turn.return_value = {
            "reply_text": "Would you like me to proceed?",
            "action_type": "order",
            "action_data": {"items": [{"name": "Maggi", "quantity": 2}]},
            "detected_language_code": "en-IN",
        }
        self.gemini.generate_action_confirmation.return_value = (
            "Should I record two Maggi packets?"
        )

        result = self.process("Sell two Maggi")

        self.assertEqual(result["action_type"], "pending_confirmation")
        self.assertTrue(result["confirmation_required"])
        self.assertEqual(result["pending_action"]["action_type"], "order")
        self.database.execute_action.assert_not_called()

    def test_explicit_confirmation_executes_pending_change_once(self):
        pending = {
            "action_type": "order",
            "action_data": {"items": [{"name": "Maggi", "quantity": 2}]},
            "raw_call_text": "Call: sell two Maggi",
        }
        self.gemini.classify_confirmation.return_value = "confirmed"
        self.database.execute_action.return_value = {
            "status": "success",
            "message": "Order recorded.",
        }
        self.gemini.generate_action_result.return_value = "Your order is recorded."

        result = self.process("Yes, go ahead", pending)

        self.database.execute_action.assert_called_once_with(
            "order",
            pending["action_data"],
            raw_call_text=pending["raw_call_text"],
        )
        self.assertIsNone(result["pending_action"])
        self.assertFalse(result["confirmation_required"])
        self.assertEqual(result["db_result"]["status"], "success")

    def test_unclear_reply_does_not_execute_or_clear_pending_change(self):
        pending = {
            "action_type": "repayment",
            "action_data": {"customer_name": "Ramesh", "amount": 100},
        }
        self.gemini.classify_confirmation.return_value = "unclear"
        self.gemini.generate_confirmation_reply.return_value = (
            "Please say yes to confirm or no to cancel."
        )

        result = self.process("How much will remain?", pending)

        self.database.execute_action.assert_not_called()
        self.assertEqual(result["pending_action"], pending)
        self.assertTrue(result["confirmation_required"])

    def test_explicit_rejection_clears_pending_without_mutation(self):
        pending = {
            "action_type": "credit_log",
            "action_data": {"customer_name": "Ramesh", "amount": 100},
        }
        self.gemini.classify_confirmation.return_value = "rejected"
        self.gemini.generate_confirmation_reply.return_value = "Cancelled."

        result = self.process("No, cancel", pending)

        self.database.execute_action.assert_not_called()
        self.assertIsNone(result["pending_action"])
        self.assertFalse(result["confirmation_required"])
        self.assertEqual(result["action_type"], "confirmation_cancelled")

    def test_confirmation_prompt_fallback_describes_pending_order(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
            service = CallGeminiService()

        message = service.generate_action_confirmation(
            "order",
            {
                "items": [{"name": "Maggi", "quantity": 2}],
                "payment_mode": "cash",
            },
            language_code="en-IN",
        )

        self.assertIn("2 x Maggi", message)
        self.assertIn("not recorded", message)
        self.assertIn("Should I proceed", message)

    def test_confirmation_fails_closed_without_gemini(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
            service = CallGeminiService()

        self.assertEqual(
            service.classify_confirmation(
                "yes",
                {"action_type": "order", "action_data": {}},
            ),
            "unclear",
        )


if __name__ == "__main__":
    unittest.main()
