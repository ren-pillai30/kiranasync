import os
import json
import warnings
from typing import Dict, List, Optional, Any

warnings.filterwarnings("ignore")

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class CallGeminiService:
    """
    Reasoning pipeline for Kirana store phone assistant powered by
    google-genai SDK and the gemini-2.5-flash model.
    """

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = model or os.getenv("GEMINI_CALL_MODEL", self.DEFAULT_MODEL)
        self.client = None
        if genai and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize genai.Client: {e}")

    def _build_system_instruction(
        self,
        inventory_items: List[Dict[str, Any]],
        customers: List[Dict[str, Any]],
        store_name: str = "Kirana Store",
    ) -> str:
        inv_str = ", ".join(
            [f"'{it['ItemName']}' (Price: ₹{it['Price']}, Stock: {it['StockQuantity']})" for it in inventory_items]
        ) or "None"

        cust_str = ", ".join(
            [f"'{c['CustomerName']}' (Udhaar Balance: ₹{c['OutstandingBalance']})" for c in customers]
        ) or "None"

        return f"""You are the friendly, intelligent AI voice assistant for '{store_name}', a local Indian Kirana (retail & grocery) store.
You are talking to a customer or shop regular on an active phone call.

PRIMARY GOALS:
1. Greet callers warmly, professionally, and naturally in their language (Hindi, Hinglish, English, Tamil, Telugu, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi).
2. Answer customer inquiries regarding product availability, prices, and existing customer credit/udhaar balances.
3. Accurately take grocery orders: identify item names from the catalog, quantities, and whether the order is to be paid in cash or added to udhaar/credit for a specific customer.
4. Record credit/udhaar operations: logging new udhaar or recording repayments.
5. Keep spoken replies natural, concise, and polite — as if speaking on a phone call. Never use markdown symbols (no asterisks, hash tags, or bullet points) in 'reply_text'.

LIVE STORE DATA:
- Active Inventory Items: [{inv_str}]
- Existing Customer Udhaar Accounts: [{cust_str}]

DOMAIN BEHAVIOR RULES:
- When a customer asks if an item is available or its price:
  State clearly if it is in stock and its price. If stock is 0 or item does not exist, politely inform them.
- When a customer orders items:
  Set action_type to "order". In action_data, populate "items" with catalog item names and positive integer quantities.
  Check if the customer mentioned paying on udhaar / credit (e.g. "khate mein likh do", "put on udhaar", "Ramesh ke account me"), set payment_mode to "udhaar" and extract customer_name. Otherwise payment_mode is "cash".
- When a customer asks to log credit without ordering goods:
  Set action_type to "credit_log", populate customer_name and amount.
- When a customer repays an outstanding balance:
  Set action_type to "repayment", populate customer_name and amount.
- When asking about their own or a customer's balance:
  Set action_type to "inquiry", inquiry_subject to "customer_balance", and state the current balance accurately.
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
    "inquiry_subject": "stock" | "price" | "customer_balance" | "general"
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
            # Fallback if SDK or key is not available
            return {
                "reply_text": f"Namaste! Aapne kaha: {clean_input}. Store assistant is online.",
                "action_type": "general",
                "action_data": {},
                "detected_language_code": language_preference,
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
        except Exception as e:
            print(f"CallGeminiService reasoning exception: {e}")
            return {
                "reply_text": "Ji, main sun raha hoon. Kya aap dobara bata sakte hain?",
                "action_type": "general",
                "action_data": {},
                "detected_language_code": language_preference,
                "error": str(e),
            }

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

