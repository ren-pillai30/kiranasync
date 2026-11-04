from typing import Any, Dict, List, Optional


MUTATING_ACTIONS = {"order", "credit_log", "repayment"}


def process_call_turn(
    *,
    user_utterance: str,
    conversation_history: Optional[List[Dict[str, str]]],
    inventory_items: List[Dict[str, Any]],
    customers: List[Dict[str, Any]],
    caller_name: str,
    language_code: str,
    gemini_service: Any,
    db_service: Any,
    pending_action: Optional[Dict[str, Any]] = None,
    raw_call_text: str = "",
) -> Dict[str, Any]:
    if pending_action:
        decision = gemini_service.classify_confirmation(
            user_utterance,
            pending_action,
            language_code=language_code,
        )
        if decision == "confirmed":
            action_type = pending_action["action_type"]
            action_data = pending_action["action_data"]
            db_result = db_service.execute_action(
                action_type,
                action_data,
                raw_call_text=pending_action.get("raw_call_text") or raw_call_text,
            )
            reply_text = gemini_service.generate_action_result(
                action_type,
                action_data,
                db_result,
                language_code=language_code,
            )
            return {
                "reply_text": reply_text,
                "action_type": f"confirmed_{action_type}",
                "action_data": action_data,
                "db_result": db_result,
                "pending_action": None,
                "confirmation_required": False,
                "detected_language_code": language_code,
            }

        if decision == "rejected":
            return {
                "reply_text": gemini_service.generate_confirmation_reply(
                    "cancelled",
                    pending_action,
                    language_code=language_code,
                ),
                "action_type": "confirmation_cancelled",
                "action_data": pending_action["action_data"],
                "db_result": None,
                "pending_action": None,
                "confirmation_required": False,
                "detected_language_code": language_code,
            }

        return {
            "reply_text": gemini_service.generate_confirmation_reply(
                "clarify",
                pending_action,
                language_code=language_code,
            ),
            "action_type": "confirmation_pending",
            "action_data": pending_action["action_data"],
            "db_result": None,
            "pending_action": pending_action,
            "confirmation_required": True,
            "detected_language_code": language_code,
        }

    result = gemini_service.process_call_turn(
        user_utterance=user_utterance,
        conversation_history=conversation_history,
        inventory_items=inventory_items,
        customers=customers,
        caller_name=caller_name,
        language_preference=language_code,
    )
    action_type = result.get("action_type", "general")
    action_data = result.get("action_data") or {}
    if action_type in MUTATING_ACTIONS:
        pending = {
            "action_type": action_type,
            "action_data": action_data,
            "raw_call_text": raw_call_text,
        }
        result.update(
            reply_text=gemini_service.generate_action_confirmation(
                action_type,
                action_data,
                language_code=result.get("detected_language_code") or language_code,
            ),
            action_type="pending_confirmation",
            db_result=None,
            pending_action=pending,
            confirmation_required=True,
        )
        return result

    result.update(
        db_result=None,
        pending_action=None,
        confirmation_required=False,
    )
    return result
