import os
import sys
import sqlite3
import re
import json
import difflib
from number_parser import parse

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

try:
    from thefuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

DB_PATH = get_resource_path('kirana.db')
CATALOG_PATH = os.path.join(os.path.abspath("."), "catalog.json")
MAPPINGS_PATH = os.path.join(os.path.abspath("."), "mappings.json")

# --- DYNAMIC LEARNING MAPPINGS ---
def load_learned_mappings():
    if not os.path.exists(MAPPINGS_PATH): return {}
    try:
        with open(MAPPINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def update_learned_mapping(raw_word, resolved_word):
    """Saves user corrections from the UI for future use."""
    mappings = load_learned_mappings()
    if len(raw_word.split()) <= 2:
        mappings[raw_word.lower()] = resolved_word.lower()
        with open(MAPPINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=4, ensure_ascii=False)

def load_fmcg_catalog():
    if not os.path.exists(CATALOG_PATH):
        default_catalog = {"Britannia Biscuit": 10, "Tata Salt 1kg": 25, "Sugar 1kg": 45, "Maggi": 14}
        with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_catalog, f, indent=4, ensure_ascii=False)
        return default_catalog
    try:
        with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def search_product_online(clean_item_name):
    """Agentic web search for real MRPs of unknown items."""
    corrected_brand = clean_item_name.title()
    price = 0
    if DDGS:
        try:
            query = f"{corrected_brand} MRP price BigBasket JioMart India"
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
            if results:
                text_corpus = " ".join([r.get('body', '') + " " + r.get('title', '') for r in results]).lower()
                price_matches = re.findall(r'(?:rs\.?|₹|inr|mrp|price)\s*[:\-\s]?\s*(?:rs\.?|₹)?\s*(\d{1,4})', text_corpus)
                if price_matches:
                    price = int(price_matches[0])
        except Exception as e:
            print(f"DDG Search Error: {e}")
    return corrected_brand, price

def get_db_records(table, column):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f'SELECT {column} FROM {table}')
    records = [row[0] for row in cursor.fetchall()]
    conn.close()
    return records

def translate_to_english(transcript):
    """Validate and normalize the English-script transcript returned by Gnani."""
    if not transcript or not transcript.strip():
        raise RuntimeError("The voice command was empty. Please try again.")

    cleaned_transcript = transcript.strip()
    if re.search(r'[\u0900-\u097f]', cleaned_transcript):
        raise RuntimeError(
            "Gnani returned a Hindi-script transcript instead of English. "
            "Use the en-IN transcription mode and try the command again."
        )
    return cleaned_transcript.lower()

def match_entity_with_score(query_text, db_records, threshold=70):
    """Finds the best fuzzy match in the database using token subset ratios."""
    if not query_text or str(query_text).strip() == "":
        return None

    def normalized_tokens(value):
        return set(re.findall(r'\w+', str(value).lower()))

    if process and fuzz:
        match = process.extractOne(query_text, db_records, scorer=fuzz.token_set_ratio)
        if match and match[1] >= threshold:
            return match[0]

    query_tokens = normalized_tokens(query_text)
    if not query_tokens:
        return None

    best_record = None
    best_score = 0
    for record in db_records:
        record_tokens = normalized_tokens(record)
        if not record_tokens:
            continue
        shared_tokens = query_tokens & record_tokens
        if query_tokens <= record_tokens or record_tokens <= query_tokens:
            score = 100
        else:
            score = 200 * len(shared_tokens) / (len(query_tokens) + len(record_tokens))
        text_score = 100 * difflib.SequenceMatcher(
            None, ' '.join(sorted(query_tokens)), ' '.join(sorted(record_tokens))
        ).ratio()
        score = max(score, text_score)
        if score > best_score:
            best_record = record
            best_score = score

    if best_score >= threshold:
        return best_record

    # Match an individually well-recognized product token even when the
    # transcript also contains unparsed command words or a spelling variant.
    best_token_record = None
    best_token_score = 0
    for record in db_records:
        record_tokens = normalized_tokens(record)
        token_score = max(
            (
                100 * difflib.SequenceMatcher(None, query_token, record_token).ratio()
                for query_token in query_tokens
                if len(query_token) >= 4
                for record_token in record_tokens
            ),
            default=0,
        )
        if token_score > best_token_score:
            best_token_record = record
            best_token_score = token_score

    return best_token_record if best_token_score >= 88 else None

_QUANTITY_UNIT_PATTERN = (
    r'\b(?:k\s*g|kg|kilo(?:s|gram|grams)?|g|grams?|lit(?:er|re)s?|ml|millilit(?:er|re)s?)\b|'
    r'किलो(?:\s?ग्राम)?|के\s?जी|ग्राम|लीटर|मिलीलीटर'
)
_CURRENCY_UNIT_PATTERN = (
    r'\b(?:rupees?|rup(?:ay|aye|ya|ai)s?|rs\.?|inr)\b|₹|रुप(?:ये|ए|या|यों)?'
)

def find_quantity_unit(text_string):
    return re.search(_QUANTITY_UNIT_PATTERN, text_string.lower())

def find_currency_unit(text_string):
    return re.search(_CURRENCY_UNIT_PATTERN, text_string.lower())

def find_quantity_marker(text_string):
    return find_quantity_unit(text_string) or find_currency_unit(text_string)

def has_quantity_unit(text_string):
    """Return whether a command names a measured quantity unit."""
    return find_quantity_unit(text_string) is not None

def has_quantity_marker(text_string):
    """Return whether a command has a measurement or currency unit."""
    return find_quantity_marker(text_string) is not None

def extract_explicit_quantity(text_string):
    """Extract a quantity when the transcript explicitly contains one."""
    quantity_marker = find_quantity_marker(text_string)
    quantity_text = (
        text_string[:quantity_marker.start()]
        if quantity_marker
        else text_string
    )
    digits = re.findall(r'\d+', quantity_text)
    if digits:
        return int(digits[0])

    parsed_text = parse(quantity_text.lower(), language='en')
    digits = re.findall(r'\d+', parsed_text)
    if digits:
        return int(digits[0])
    return None

def extract_quantity(text_string):
    """Extract the amount, defaulting to one only when no amount marker exists."""
    quantity = extract_explicit_quantity(text_string)
    if quantity is not None:
        return quantity
    return None if find_quantity_marker(text_string) else 1

def extract_hindi_quantity(transcript):
    """Parse a full Hindi transcript, ignoring trailing command particles."""
    normalized_transcript = parse(transcript, language='hi')
    quantity_marker = find_quantity_marker(normalized_transcript)
    if not quantity_marker:
        leading_number = re.match(r'\s*(\d+)\b', normalized_transcript)
        return int(leading_number.group(1)) if leading_number else None

    quantity_text = normalized_transcript[:quantity_marker.start()]
    digits = re.findall(r'\d+', quantity_text)
    if not digits:
        original_marker = find_quantity_marker(transcript)
        if not original_marker:
            return None
        quantity_text = parse(
            transcript[:original_marker.start()],
            language='en',
        )
        digits = re.findall(r'\d+', quantity_text)
    return int(digits[0]) if digits else None

def determine_intent(combined_text):
    text_lower = combined_text.lower()
    credit_keywords = ['account', 'balance', 'credit', 'deposit', 'due', 'owe']
    restock_keywords = [
        'restock', 'add', 'buy', 'bought', 'purchase', 'receive', 'received',
        'store', 'arrive', 'arrived', 'delivery', 'delivered', 'came', 'come',
        'came in', 'come in', 'bring',
    ]
    if any(kw in text_lower for kw in credit_keywords): return 'credit'
    if any(kw in text_lower for kw in restock_keywords): return 'restock'
    return 'sell'

def isolate_clean_entity(text_string):
    """Strip English command words, quantities, and units from translated text."""
    stop_words = {
        'account', 'balance', 'credit', 'deposit', 'due', 'rupees', 'rs', 'rupee',
        'restock', 'add', 'buy', 'bought', 'purchase', 'receive', 'received', 'store', 'bring',
        'arrive', 'arrived', 'delivery', 'delivered', 'came', 'come', 'give', 'remove', 'dispatch',
        'take', 'put', 'send', 'pay', 'sell', 'sells', 'sold', 'has', 'have', 'had', 'been',
        'of', 'for', 'to', 'in', 'the', 'a', 'an', 'is', 'and', 'with', 'some', 'my', 'on',
        'liter', 'liters', 'litre', 'litres', 'ml', 'kg', 'kilo', 'kilos', 'kilogram',
        'kilograms', 'gram', 'grams',
        'packet', 'packets', 'pack', 'packs', 'piece', 'pieces', 'box', 'boxes',
        'hundred', 'thousand',
    }
    normalized_text = re.sub(r'\bk\s+g\b', 'kg', text_string.lower())
    normalized_text = parse(normalized_text, language='en')
    words = re.findall(r'\w+', normalized_text)
    clean_words = [w for w in words if w not in stop_words and not re.match(r'\d+', w)]
    return " ".join(clean_words).title()

def parse_and_execute(raw_transcript, quantity_override=None, interpretation=None):
    if interpretation is None:
        try:
            english_meaning = translate_to_english(raw_transcript)
        except RuntimeError as exc:
            return {
                "status": "failed",
                "action": "translation_failed",
                "message": str(exc),
            }

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    db_items = get_db_records('Inventory', 'ItemName')
    db_customers = get_db_records('CustomerCredit', 'CustomerName')

    if interpretation is not None:
        if not isinstance(interpretation, dict):
            conn.close()
            return {
                "status": "failed",
                "action": "interpretation_invalid",
                "message": "The command could not be safely interpreted. No changes were made.",
            }
        intent = interpretation.get("action")
        clean_translated_entity = interpretation.get("entity")
        quantity_or_amount = interpretation.get("quantity")
        if intent not in {"sell", "restock", "credit", "unknown"}:
            conn.close()
            return {
                "status": "failed",
                "action": "interpretation_invalid",
                "message": "The command could not be safely interpreted. No changes were made.",
            }
        if intent == "unknown":
            conn.close()
            return {
                "status": "failed",
                "action": "intent_unrecognized",
                "message": "Could not determine the requested action. No changes were made.",
            }
        if not isinstance(clean_translated_entity, str) or not clean_translated_entity.strip():
            conn.close()
            return {
                "status": "failed",
                "action": "entity_unrecognized",
                "message": "Could not identify the requested item or customer. No changes were made.",
            }
        clean_translated_entity = clean_translated_entity.strip()
        if (
            not isinstance(quantity_or_amount, int)
            or isinstance(quantity_or_amount, bool)
            or quantity_or_amount <= 0
        ):
            conn.close()
            return {
                "status": "failed",
                "action": "quantity_unrecognized",
                "message": "Could not recognize a positive whole-number quantity. No changes were made.",
            }
        target_item = (
            match_entity_with_score(clean_translated_entity, db_items, threshold=70)
            if intent in {"sell", "restock"}
            else None
        )
        target_customer = (
            match_entity_with_score(clean_translated_entity, db_customers, threshold=70)
            if intent == "credit"
            else None
        )
    else:
        # Preserve the local parser path for callers that do not provide an interpretation.
        clean_translated_entity = isolate_clean_entity(english_meaning)
        target_item = match_entity_with_score(clean_translated_entity, db_items, threshold=70)
        target_customer = match_entity_with_score(clean_translated_entity, db_customers, threshold=70)
        intent = determine_intent(english_meaning)
        quantity_or_amount = (
            quantity_override
            if quantity_override is not None
            else extract_quantity(english_meaning)
        )

    if quantity_or_amount is None:
        conn.close()
        return {
            "status": "failed",
            "action": "quantity_unrecognized",
            "message": "Could not recognize the quantity. Please repeat the amount clearly.",
        }

    final_unknown_entity = clean_translated_entity

    # --- EXECUTE TRANSACTIONS ---
    if intent == 'credit' or target_customer:
        amount = quantity_or_amount
        if not target_customer:
            target_customer = final_unknown_entity or "Unknown Customer"
            cursor.execute('INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES (?, ?)', (target_customer, amount))
            message = f"Created new account for {target_customer} with Rs {amount} balance."
        else:
            cursor.execute('SELECT OutstandingBalance FROM CustomerCredit WHERE CustomerName = ?', (target_customer,))
            row = cursor.fetchone()
            current_bal = row[0] if row else 0
            new_bal = current_bal + amount
            cursor.execute('UPDATE CustomerCredit SET OutstandingBalance = ? WHERE CustomerName = ?', (new_bal, target_customer))
            message = f"Added Rs {amount} to {target_customer}. New Balance: Rs {new_bal}."

        cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (raw_transcript, amount))
        conn.commit()
        conn.close()
        return {"status": "success", "action": "udhaar_added", "message": message}

    elif intent == 'restock':
        if target_item:
            cursor.execute('SELECT StockQuantity FROM Inventory WHERE ItemName = ?', (target_item,))
            row = cursor.fetchone()
            current_stock = int(row[0]) if row else 0
            new_stock = current_stock + quantity_or_amount
            cursor.execute('UPDATE Inventory SET StockQuantity = ? WHERE ItemName = ?', (new_stock, target_item))
            cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (raw_transcript, 0))
            conn.commit()
            conn.close()
            return {"status": "success", "action": "inventory_restocked", "message": f"Restocked {quantity_or_amount} {target_item}. Total stock: {new_stock}."}
        else:
            web_name, web_price = search_product_online(final_unknown_entity)
            conn.close()
            return {
                "status": "pending_confirmation",
                "action": "confirm_restock",
                "message": f"Internet Search: Found '{web_name}'. Please confirm details.",
                "draft": {
                    "ItemName": web_name,
                    "Price": web_price,
                    "StockQuantity": quantity_or_amount,
                    "RawCommand": raw_transcript
                }
            }

    else:
        if target_item:
            cursor.execute('SELECT StockQuantity, Price FROM Inventory WHERE ItemName = ?', (target_item,))
            result = cursor.fetchone()
            if result and int(result[0]) >= quantity_or_amount:
                new_stock = int(result[0]) - quantity_or_amount
                cursor.execute('UPDATE Inventory SET StockQuantity = ? WHERE ItemName = ?', (new_stock, target_item))
                cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (raw_transcript, result[1] * quantity_or_amount))
                conn.commit()
                conn.close()
                return {"status": "success", "action": "inventory_updated", "message": f"Sold {quantity_or_amount} {target_item}. Stock left: {new_stock}."}
            elif result:
                conn.close()
                return {"status": "failed", "action": "out_of_stock", "message": f"Not enough {target_item} in stock! Only {result[0]} left."}
        else:
            conn.close()
            return {
                "status": "failed",
                "action": "item_not_found",
                "message": f"Could not match '{final_unknown_entity}' to an inventory item. No stock was changed.",
            }