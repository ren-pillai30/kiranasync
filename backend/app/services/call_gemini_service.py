import os
import json
import logging
import warnings
from typing import Dict, List, Optional, Any

warnings.filterwarnings("ignore")

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger(__name__)


class CallGeminiService:
    """
    Reasoning pipeline for Kirana store phone assistant powered by
    google-genai SDK and the gemini-2.5-flash model.
    """

    DEFAULT_MODEL = "gemini-3.5-flash-lite"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        if os.getenv("GOOGLE_API_KEY") == "no":
            os.environ.pop("GOOGLE_API_KEY", None)
        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        if not resolved_key or resolved_key == "no":
            resolved_key = os.getenv("GOOGLE_API_KEY")
        self.api_key = resolved_key if resolved_key and resolved_key != "no" else None
        self.model = model or os.getenv("GEMINI_CALL_MODEL") or os.getenv("GEMINI_MODEL") or self.DEFAULT_MODEL
        self.client = None
        self.initialization_error = None
        if genai is None:
            self.initialization_error = "The google-genai package is not installed."
        elif not self.api_key:
            self.initialization_error = "GEMINI_API_KEY or GOOGLE_API_KEY is not configured."
        else:
            try:
                self.client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(timeout=20_000),
                )
            except Exception:
                logger.exception("Failed to initialize the Gemini client")
                self.initialization_error = "The Gemini client could not be initialized."

    def _build_system_instruction(
        self,
        inventory_items: List[Dict[str, Any]],
        customers: List[Dict[str, Any]],
        store_name: str = "Kirana Store",
    ) -> str:
        inv_str = ", ".join(
            [
                (
                    f"'{it['ItemName']}'"
                    + (f" / '{it['ItemNameHindi']}'" if it.get('ItemNameHindi') else "")
                    + f" (Price: ₹{it['Price']}, Stock: {it['StockQuantity']})"
                )
                for it in inventory_items
            ]
        ) or "None"

        cust_str = ", ".join(
            [
                (
                    f"'{c['CustomerName']}'"
                    + (f" / '{c['CustomerNameHindi']}'" if c.get('CustomerNameHindi') else "")
                    + f" (Udhaar Balance: ₹{c['OutstandingBalance']})"
                )
                for c in customers
            ]
        ) or "None"

        return f"""You are the friendly, intelligent AI voice assistant for '{store_name}', a local Indian Kirana (retail & grocery) store.
You are talking to a customer or shop regular on an active phone call.

PRIMARY GOALS:
1. Greet callers warmly, professionally, and naturally in their language (Hindi, Hinglish, English, Tamil, Telugu, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi).
2. Answer customer inquiries regarding product availability, prices, and existing customer credit/udhaar balances.
3. Accurately take grocery orders: identify item names from the catalog, quantities, and whether the order is to be paid in cash or added to udhaar/credit for a specific customer.
4. Record credit/udhaar operations: logging new udhaar or recording repayments, but only after explicit caller confirmation.
5. Keep spoken replies natural, concise, and polite — as if speaking on a phone call. Never use markdown symbols (no asterisks, hash tags, or bullet points) in 'reply_text'.

LIVE STORE DATA:
- Active Inventory Items: [{inv_str}]
- Existing Customer Udhaar Accounts: [{cust_str}]

DOMAIN BEHAVIOR RULES:
- When a customer asks if an item is available or its price:
  State clearly if it is in stock and its price. If stock is 0 or item does not exist, politely inform them.
- When a customer asks for or orders an item with a specific measurement/size (e.g. "1 kg salt", "500ml oil", "2 litre milk"):
  1. If the exact requested measurement is NOT available in active inventory, but other measurements/sizes of that product exist (e.g. only 300g, 500g, or 2 kg exist in catalog, but not 1 kg):
     - In 'reply_text', clearly tell the customer that the exact measurement is not available, and highlight which other measurements/sizes are in stock (e.g. "1 kg salt available nahi hai, par hamare paas 500g aur 2 kg available hai. Kya aapko inme se chahiye?").
     - Set action_type to "inquiry", inquiry_subject to "stock_measurement_mismatch", and in action_data include "requested_measurement" and "available_measurements". Do not execute an order for the wrong size without customer confirmation.
  2. If the exact measurement is in stock, proceed with the order or inquiry as requested.
- When a customer orders items:
  Set action_type to "order". In action_data, populate "items" with catalog item names and positive integer quantities.
  Never state or imply that an order has been recorded. Summarize the requested items, quantities, payment mode, and customer if applicable, then ask the caller for explicit confirmation.
  Check if the customer mentioned paying on udhaar / credit (e.g. "khate mein likh do", "put on udhaar", "Ramesh ke account me"), set payment_mode to "udhaar" and extract customer_name. Otherwise payment_mode is "cash".
- When a customer asks to log credit without ordering goods:
  Set action_type to "credit_log", populate customer_name and amount. Ask for explicit confirmation; do not imply the balance was changed.
- When a customer repays an outstanding balance:
  Set action_type to "repayment", populate customer_name and amount. Ask for explicit confirmation; do not imply the balance was changed.
- When asking about their own or a customer's balance:
  Set action_type to "inquiry", inquiry_subject to "customer_balance", and state the current balance accurately.
- When a customer asks about their current bill total / "kitna hua" / "mera bill":
  Set action_type to "inquiry", inquiry_subject to "bill_total". In reply_text, summarize the items ordered so far and announce the running total naturally.
- For greeting or general chat:
  Set action_type to "general".

RESPONSE FORMAT:
You MUST respond strictly in valid JSON matching this exact structure:
{{
  "reply_text": "Spoken sentence to the customer in the same language and script they spoke",
  "action_type": "inquiry" | "order" | "credit_log" | "repayment" | "general",
  "action_data": {{
    "items": [{{"name": "Exact Catalog Item Name", "quantity": 1}}],
    "customer_name": "Customer Name or empty string",
    "amount": 0.0,
    "payment_mode": "cash" | "udhaar",
    "inquiry_subject": "stock" | "price" | "customer_balance" | "bill_total" | "general"
  }},
  "detected_language_code": "hi-IN" | "en-IN" | "ta-IN" | "te-IN" | "kn-IN" | "ml-IN" | "mr-IN" | "bn-IN" | "gu-IN" | "pa-IN"
}}"""

    def process_call_turn(
        self,
        user_utterance: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        inventory_items: Optional[List[Dict[str, Any]]] = None,
        customers: Optional[List[Dict[str, Any]]] = None,
        caller_name: Optional[str] = None,
        language_preference: str = "hi-IN",
    ) -> Dict[str, Any]:
        """
        Processes one conversational turn of the phone call using gemini-2.5-flash.
        Returns parsed action and spoken reply.
        """
        clean_input = (user_utterance or "").strip()
        if not clean_input:
            return {
                "reply_text": "Aapki aawaz nahi aayi, kripya dobara bolein.",
                "action_type": "general",
                "action_data": {},
                "detected_language_code": language_preference,
            }

        inv_items = inventory_items or []
        cust_list = customers or []
        system_instruction = self._build_system_instruction(inv_items, cust_list)

        # Build conversation context
        history_prompts = []
        if conversation_history:
            for turn in conversation_history[-6:]:  # Keep recent 6 turns
                role = turn.get("role", "customer")
                text = turn.get("text", "")
                if text:
                    history_prompts.append(f"{role.capitalize()}: {text}")

        current_prompt = f"Caller Name (if known): {caller_name or 'Unknown'}\n"
        if history_prompts:
            current_prompt += "Recent Call History:\n" + "\n".join(history_prompts) + "\n\n"
        current_prompt += f"Latest Customer Utterance: \"{clean_input}\"\nRespond with JSON:"

        if not self.client:
            return {
                "reply_text": "",
                "action_type": "service_error",
                "action_data": {},
                "detected_language_code": language_preference,
                "error": self.initialization_error or "Gemini intent parsing is unavailable.",
            }

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.2,
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=current_prompt,
                config=config,
            )

            raw_text = (response.text or "").strip()
            data = json.loads(raw_text)

            # Sanitize and validate fields
            reply_text = data.get("reply_text") or "Ji bilkul, main samajh gaya."
            action_type = data.get("action_type") or "general"
            action_data = data.get("action_data") or {}
            detected_lang = data.get("detected_language_code") or language_preference

            # Ensure clean spoken reply without markdown asterisks
            reply_text = reply_text.replace("**", "").replace("*", "").replace("#", "").strip()

            return {
                "reply_text": reply_text,
                "action_type": action_type,
                "action_data": action_data,
                "detected_language_code": detected_lang,
            }
        except Exception:
            logger.exception("Gemini failed to process a Call Simulator turn")
            return {
                "reply_text": "",
                "action_type": "service_error",
                "action_data": {},
                "detected_language_code": language_preference,
                "error": "Gemini intent parsing failed. Check the Gemini API key, model, and quota.",
            }

    def classify_confirmation(
        self,
        user_utterance: str,
        pending_action: Dict[str, Any],
        language_code: str = "hi-IN",
    ) -> str:
        if not self.client:
            return "unclear"
        prompt = (
            "Classify the caller's latest utterance as an explicit confirmation, an explicit "
            "rejection/cancellation, or unclear in response to the pending business action. "
            "Only return confirmed or rejected when the caller's intent is unambiguous. "
            "A new request, question, hesitation, or unrelated reply is unclear. "
            f"Language: {language_code}\n"
            f"Pending action: {json.dumps(pending_action, ensure_ascii=False)}\n"
            f"Caller utterance: {json.dumps(user_utterance, ensure_ascii=False)}"
        )
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0,
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "decision": {
                                "type": "STRING",
                                "enum": ["confirmed", "rejected", "unclear"],
                            }
                        },
                        "required": ["decision"],
                    },
                ),
            )
            decision = json.loads((response.text or "").strip()).get("decision")
            return decision if decision in {"confirmed", "rejected", "unclear"} else "unclear"
        except Exception as exc:
            print(f"CallGeminiService confirmation classification failed: {exc}")
            return "unclear"

    def _generate_conversational_reply(self, prompt: str, language_code: str) -> Optional[str]:
        if not self.client:
            return None
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=(
                    f"Write one concise, natural phone-conversation sentence in language "
                    f"{language_code}. Preserve all names, quantities, and amounts exactly. "
                    "Do not use markdown.\n" + prompt
                ),
                config=types.GenerateContentConfig(temperature=0.2),
            )
            return (response.text or "").strip() or None
        except Exception as exc:
            print(f"CallGeminiService conversational response failed: {exc}")
            return None

    def generate_action_confirmation(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        language_code: str = "hi-IN",
    ) -> str:
        fallback = self._confirmation_fallback(action_type, action_data, language_code)
        if not self.client:
            return fallback
        prompt = (
            f"Action: {action_type}. Details: {json.dumps(action_data, ensure_ascii=False)}\n"
            "Create one natural spoken sentence for the caller that briefly summarizes this "
            "exact change, explicitly says it has not been recorded, and asks whether to "
            "proceed. Never say or imply it is already complete."
        )
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=(
                    f"Use language {language_code}. Preserve names, quantities, and amounts exactly. "
                    "Return JSON only with message, asks_confirmation, and says_not_recorded.\n"
                    + prompt
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "message": {"type": "STRING"},
                            "asks_confirmation": {"type": "BOOLEAN"},
                            "says_not_recorded": {"type": "BOOLEAN"},
                        },
                        "required": ["message", "asks_confirmation", "says_not_recorded"],
                    },
                ),
            )
            data = json.loads((response.text or "").strip())
            message = data.get("message")
            if (
                isinstance(message, str)
                and message.strip()
                and data.get("asks_confirmation") is True
                and data.get("says_not_recorded") is True
            ):
                return message.strip()
        except Exception as exc:
            print(f"CallGeminiService confirmation prompt failed: {exc}")
        return fallback

    @staticmethod
    def _confirmation_fallback(
        action_type: str,
        action_data: Dict[str, Any],
        language_code: str,
    ) -> str:
        if action_type == "order":
            requested = ", ".join(
                f"{item.get('quantity', 1)} x {item.get('name') or item.get('entity') or 'item'}"
                for item in action_data.get("items", [])
                if isinstance(item, dict)
            ) or "the requested items"
            payment = action_data.get("payment_mode") or "cash"
            customer = action_data.get("customer_name")
            details = f"{requested} on {payment}"
            if customer:
                details += f" for {customer}"
            hi_details = requested
            if customer:
                hi_details += f", {customer} के खाते में"
            if language_code == "hi-IN":
                return f"आपने {hi_details} का ऑर्डर कहा है। अभी रिकॉर्ड नहीं किया है। क्या मैं इसे दर्ज करूँ?"
            return f"You asked for {details}. I have not recorded it yet. Should I proceed?"

        customer = action_data.get("customer_name") or "the customer"
        amount = action_data.get("amount", 0)
        if language_code == "hi-IN":
            if action_type == "repayment":
                return f"आपने {customer} से ₹{amount} की अदायगी दर्ज करने को कहा है। अभी दर्ज नहीं किया है। क्या मैं आगे बढ़ूँ?"
            return f"आपने {customer} के खाते में ₹{amount} जोड़ने को कहा है। अभी दर्ज नहीं किया है। क्या मैं आगे बढ़ूँ?"
        operation = "record a repayment from" if action_type == "repayment" else "add credit to"
        return f"You asked me to {operation} {customer} for ₹{amount}. I have not recorded it yet. Should I proceed?"

    def generate_confirmation_reply(
        self,
        outcome: str,
        pending_action: Dict[str, Any],
        language_code: str = "hi-IN",
    ) -> str:
        generated = self._generate_conversational_reply(
            f"Respond naturally that the pending store change is {outcome}. Do not perform "
            "or claim any database action. Pending action: "
            f"{json.dumps(pending_action, ensure_ascii=False)}",
            language_code,
        )
        if generated:
            return generated
        if outcome == "cancelled":
            return "ठीक है, मैंने इसे रद्द कर दिया है।" if language_code == "hi-IN" else "Okay, I have cancelled it."
        return "कृपया हाँ या ना में बताइए।" if language_code == "hi-IN" else "Please say yes to confirm or no to cancel."

    def generate_action_result(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        db_result: Dict[str, Any],
        language_code: str = "hi-IN",
    ) -> str:
        generated = self._generate_conversational_reply(
            "The caller explicitly confirmed this store change. Briefly report the actual "
            "result without adding facts. "
            f"Action: {action_type}. Details: {json.dumps(action_data, ensure_ascii=False)}. "
            f"Database result: {json.dumps(db_result, ensure_ascii=False)}",
            language_code,
        )
        return generated or str(db_result.get("message") or "The confirmed change was processed.")

    def generate_call_greeting(
        self,
        caller_name: Optional[str] = None,
        language_code: str = "hi-IN",
    ) -> str:
        """
        Generates an initial greeting when the phone call connects.
        """
        name_part = f" {caller_name}" if caller_name else ""
        if language_code == "en-IN":
            return f"Hello{name_part}! Welcome to Kirana store. How can I help you today?"
        elif language_code == "ta-IN":
            return f"வணக்கம்{name_part}! மளிகை கடைக்கு வரவேற்கிறோம். நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?"
        elif language_code == "te-IN":
            return f"నమస్కారం{name_part}! కిరాణా దుకాణానికి స్వాగతం. నేను మీకు ఎలా సహాయపడగలను?"
        elif language_code == "kn-IN":
            return f"ನಮಸ್ಕಾರ{name_part}! ಕಿರಾಣಿ ಅಂಗಡಿಗೆ ಸುಸ್ವಾಗತ. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
        elif language_code == "mr-IN":
            return f"नमस्कार{name_part}! किराणा दुकानात आपले स्वागत आहे. मी आपली काय मदत करू शकतो?"
        elif language_code == "bn-IN":
            return f"নমস্কার{name_part}! মুদির দোকানে স্বাগতম। আমি আপনাকে কীভাবে সাহায্য করতে পারি?"
        else:
            return f"नमस्ते{name_part}! किराना स्टोर में आपका स्वागत है। बताइए आज क्या सेवा करूँ?"
