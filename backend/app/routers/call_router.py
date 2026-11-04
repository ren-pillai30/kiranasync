import os
import json
import uuid
import base64
import time
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from backend.app.services.gnani_service import GnaniService
from backend.app.services.call_gemini_service import CallGeminiService
from backend.app.services.call_db_service import CallDBService
from backend.app.services.call_conversation import process_call_turn

router = APIRouter(tags=["Call Simulator"])

gnani_service = GnaniService()
gemini_service = CallGeminiService()
db_service = CallDBService()
REST_CALL_SESSIONS: Dict[str, Dict[str, Any]] = {}


class SimulateCallRequest(BaseModel):
    user_input: str
    caller_name: Optional[str] = "Customer"
    language_code: Optional[str] = "hi-IN"
    conversation_history: Optional[List[Dict[str, str]]] = []
    session_id: Optional[str] = None


class CallStartRequest(BaseModel):
    caller_name: Optional[str] = "Customer"
    language_code: Optional[str] = "hi-IN"


@router.get("/api/call/status")
def get_call_system_status():
    """
    Returns the readiness status of the Call Simulator backend services.
    """
    has_gnani = bool(os.getenv("GNANI_API_KEY"))
    has_gemini = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    return {
        "status": "ready" if (has_gnani and has_gemini) else "partially_configured",
        "gnani_stt_tts_available": has_gnani,
        "gemini_reasoning_available": has_gemini,
        "model": gemini_service.model,
        "supported_languages": gnani_service.SUPPORTED_LANGUAGES,
    }


@router.post("/api/call/start")
def start_call_session(request: CallStartRequest):
    session_id = uuid.uuid4().hex
    REST_CALL_SESSIONS[session_id] = {
        "pending_action": None,
        "order_items": [],
        "last_access": time.time(),
    }
    caller_name = request.caller_name or "Customer"
    language_code = request.language_code or "hi-IN"
    greeting = gemini_service.generate_call_greeting(caller_name, language_code)
    return {
        "status": "success",
        "session_id": session_id,
        "reply_text": greeting,
        "audio_base64": gnani_service.synthesize_speech_base64(
            greeting,
            language_code=language_code,
        ),
    }


@router.post("/api/call/simulate")
def simulate_call_turn(request: SimulateCallRequest):
    """
    REST fallback endpoint to test a call turn without WebSockets.
    """
    now = time.time()
    expired = [
        session_id
        for session_id, state in REST_CALL_SESSIONS.items()
        if now - state["last_access"] > 1800
    ]
    for session_id in expired:
        REST_CALL_SESSIONS.pop(session_id, None)

    session_id = request.session_id or uuid.uuid4().hex
    state = REST_CALL_SESSIONS.setdefault(
        session_id,
        {"pending_action": None, "order_items": [], "last_access": now},
    )
    state["last_access"] = now
    context = db_service.get_store_context()
    result = process_call_turn(
        user_utterance=request.user_input,
        conversation_history=request.conversation_history,
        inventory_items=context["inventory"],
        customers=context["customers"],
        caller_name=request.caller_name or "Customer",
        language_code=request.language_code or "hi-IN",
        gemini_service=gemini_service,
        db_service=db_service,
        pending_action=state["pending_action"],
        raw_call_text=f"Call ({request.caller_name}): {request.user_input}",
    )
    state["pending_action"] = result.pop("pending_action", None)
    db_result = result.get("db_result")
    if (
        db_result
        and db_result.get("status") == "success"
        and db_result.get("action") == "order_placed"
    ):
        state["order_items"].extend(db_result.get("items") or [])

    reply_text = result.get("reply_text", "")
    target_lang = result.get("detected_language_code") or request.language_code or "hi-IN"
    audio_b64 = gnani_service.synthesize_speech_base64(reply_text, language_code=target_lang)

    result.update({
        "status": "success",
        "session_id": session_id,
        "reply_text": reply_text,
        "audio_base64": audio_b64,
        "detected_language_code": target_lang,
        "current_bill": {
            "items": state["order_items"],
            "total": sum(float(item.get("item_total") or 0) for item in state["order_items"]),
        },
    })
    return result


@router.websocket("/ws/call")
async def call_websocket_endpoint(websocket: WebSocket):
    """
    Real-time bidirectional WebSocket endpoint for the Virtual Kirana Call Simulator.
    Accepts text or audio chunks, coordinates STT -> Gemini Reasoning -> DB Sync -> TTS,
    and streams responses back to the client.
    """
    await websocket.accept()

    session_id = uuid.uuid4().hex[:8]
    session_data = {
        "session_id": session_id,
        "caller_name": "Customer",
        "language_code": "hi-IN",
        "conversation_history": [],
        "call_active": True,
        "order_items": [],
        "total_bill": 0.0,
        "pending_action": None,
    }

    try:
        while True:
            # Can receive text or binary frame
            message = await websocket.receive()
            msg_type = message.get("type")

            if msg_type == "websocket.disconnect":
                break

            text_payload = message.get("text")
            bytes_payload = message.get("bytes")

            data = {}
            if text_payload:
                try:
                    data = json.loads(text_payload)
                except Exception:
                    data = {"type": "text_input", "text": text_payload}
            elif bytes_payload:
                # Raw audio binary sent over WS
                data = {"type": "binary_audio", "bytes": bytes_payload}

            action = data.get("type", "text_input")

            # 1. START CALL
            if action == "start_call":
                session_data["caller_name"] = data.get("customer_name") or session_data["caller_name"]
                session_data["language_code"] = data.get("language_code") or session_data["language_code"]
                session_data["conversation_history"] = []
                session_data["call_active"] = True

                greeting_text = gemini_service.generate_call_greeting(
                    caller_name=session_data["caller_name"],
                    language_code=session_data["language_code"],
                )
                session_data["conversation_history"].append({"role": "assistant", "text": greeting_text})

                audio_b64 = gnani_service.synthesize_speech_base64(
                    greeting_text, language_code=session_data["language_code"]
                )

                await websocket.send_json({
                    "type": "call_connected",
                    "session_id": session_id,
                    "caller_name": session_data["caller_name"],
                    "language_code": session_data["language_code"],
                    "reply_text": greeting_text,
                    "audio_base64": audio_b64,
                    "mime_type": "audio/wav",
                })
                continue

            # 2. END CALL
            elif action == "end_call":
                session_data["call_active"] = False
                goodbye_text = "धन्यवाद! किराना स्टोर पर कॉल करने के लिए शुक्रिया।"
                if session_data["language_code"] == "en-IN":
                    goodbye_text = "Thank you for calling Kirana store. Have a great day!"

                audio_b64 = gnani_service.synthesize_speech_base64(
                    goodbye_text, language_code=session_data["language_code"]
                )

                await websocket.send_json({
                    "type": "call_ended",
                    "session_id": session_id,
                    "reply_text": goodbye_text,
                    "audio_base64": audio_b64,
                })
                continue

            # 3. EXTRACT USER UTTERANCE (from audio or text)
            user_text = ""
            lang = data.get("language_code") or session_data["language_code"]

            if action == "audio_input":
                # Audio passed as base64 string
                raw_b64 = data.get("audio_data") or data.get("audio_base64", "")
                if raw_b64:
                    try:
                        audio_bytes = base64.b64decode(raw_b64)
                        user_text = gnani_service.transcribe_audio_bytes(audio_bytes, language_code=lang) or ""
                    except Exception as err:
                        print(f"Error decoding base64 audio: {err}")
                        user_text = ""

                # Notify client of transcribed speech immediately
                await websocket.send_json({
                    "type": "transcript",
                    "role": "customer",
                    "text": user_text or "(No speech detected)",
                })

                if not user_text.strip():
                    await websocket.send_json({
                        "type": "error",
                        "error": "No clear speech detected. Please speak closer to your microphone.",
                    })
                    continue

            elif action == "binary_audio":
                audio_bytes = data.get("bytes")
                if audio_bytes:
                    user_text = gnani_service.transcribe_audio_bytes(audio_bytes, language_code=lang) or ""
                await websocket.send_json({
                    "type": "transcript",
                    "role": "customer",
                    "text": user_text or "(No speech detected)",
                })
                if not user_text.strip():
                    continue

            else:
                user_text = data.get("text", "").strip()

            if not user_text:
                continue

            # Add customer turn to history
            session_data["conversation_history"].append({"role": "customer", "text": user_text})

            # Fetch fresh store context
            context = db_service.get_store_context()

            turn_result = process_call_turn(
                user_utterance=user_text,
                conversation_history=session_data["conversation_history"],
                inventory_items=context["inventory"],
                customers=context["customers"],
                caller_name=session_data["caller_name"],
                language_code=lang,
                gemini_service=gemini_service,
                db_service=db_service,
                pending_action=session_data["pending_action"],
                raw_call_text=f"Call ({session_data['caller_name']}): {user_text}",
            )
            session_data["pending_action"] = turn_result.get("pending_action")
            reply_text = turn_result.get("reply_text", "")
            action_type = turn_result.get("action_type", "general")
            action_data = turn_result.get("action_data", {})
            detected_lang = turn_result.get("detected_language_code") or lang
            db_result = turn_result.get("db_result")

            # Accumulate bill items when order succeeds
            if db_result and db_result.get("status") == "success" and db_result.get("action") == "order_placed":
                for it in (db_result.get("items") or []):
                    session_data["order_items"].append({
                        "item_name": it.get("item_name", ""),
                        "quantity": it.get("quantity", 1),
                        "unit_price": it.get("unit_price", 0),
                        "item_total": it.get("item_total", 0),
                    })
                session_data["total_bill"] = sum(
                    it["item_total"] for it in session_data["order_items"]
                )

            # Record assistant turn in history
            session_data["conversation_history"].append({"role": "assistant", "text": reply_text})

            # Synthesize voice output for the assistant
            audio_b64 = gnani_service.synthesize_speech_base64(
                reply_text, language_code=detected_lang
            )

            # Stream response back
            await websocket.send_json({
                "type": "call_response",
                "session_id": session_id,
                "customer_text": user_text,
                "reply_text": reply_text,
                "audio_base64": audio_b64,
                "mime_type": "audio/wav",
                "action_type": action_type,
                "action_data": action_data,
                "db_result": db_result,
                "confirmation_required": turn_result.get("confirmation_required", False),
                "language_code": detected_lang,
                "current_bill": {
                    "items": session_data["order_items"],
                    "total": session_data["total_bill"],
                },
            })

    except WebSocketDisconnect:
        # Graceful disconnection
        pass
    except Exception as e:
        print(f"Call WebSocket exception: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": f"Internal server error: {str(e)}",
            })
        except Exception:
            pass
