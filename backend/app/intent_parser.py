import os
import sys
import sqlite3
import re
import difflib
import json
import requests
import unicodedata
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

DB_PATH = get_resource_path('kirana.db')
CATALOG_PATH = os.path.join(os.path.abspath("."), "catalog.json")

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

def normalize_product_locally(raw_phonetic_name):
    catalog = load_fmcg_catalog()
    best_match, highest_ratio = None, 0.0
    for brand, price in catalog.items():
        ratio = difflib.SequenceMatcher(None, raw_phonetic_name.lower(), brand.lower()).ratio()
        if ratio > 0.60 and ratio > highest_ratio:
            highest_ratio = ratio
            best_match = (brand, price)
    return best_match if best_match else (raw_phonetic_name.title(), 0)

# --- HYBRID AGENTIC SCRAPER ---
def search_product_online(phonetic_name):
    """Gnani Evon LLM standardizes product name and DuckDuckGo finds MRP."""
    api_key = os.getenv("GNANI_API_KEY")
    corrected_brand = phonetic_name.title()

    # STEP 1: Dynamic LLM Cleaning & Spelling Correction
    if api_key:
        prompt = f"""
        A Kirana store owner dictated a voice command in Hindi/Hinglish: "{phonetic_name}".
        Extract only the core commercial brand or FMCG product name being referred to. 
        Ignore filler words, numerical quantities, units, and speech-to-text noise artifacts.
        Return ONLY the clean commercial brand string. No quotes, no markdown, no other text.
        Example: "पचास हिडेंसी इकाई है" -> Parle Hide & Seek Biscuit
        Example: "अस्सी मैगी बेच दी" -> Maggi
        """
        try:
            headers = {"Content-Type": "application/json", "X-API-Key-ID": api_key}
            payload = {
                "model": "evon-v3.3",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }
            res = requests.post("https://api.vachana.ai/v1/chat/completions", headers=headers, json=payload, timeout=5)
            if res.status_code == 200:
                corrected_brand = res.json()['choices'][0]['message']['content'].strip(' "\'')
        except Exception as e:
            print(f"LLM Spelling Correction Error: {e}")

    # STEP 2: DuckDuckGo Live Price Extraction
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

# --- TRANSLITERATION & GRAMMAR MAPS ---
DEVANAGARI_MAP = {
    'अ':'a', 'आ':'aa', 'इ':'i', 'ई':'ee', 'उ':'u', 'ऊ':'oo', 'ए':'e', 'ऐ':'ai', 'ओ':'o', 'औ':'au',
    'क':'k', 'ख':'kh', 'ग':'g', 'घ':'gh', 'च':'ch', 'छ':'chh', 'ज':'j', 'झ':'jh',
    'ट':'t', 'ठ':'th', 'ड':'d', 'ढ':'dh', 'त':'t', 'थ':'th', 'द':'d', 'ध':'dh', 'न':'n',
    'प':'p', 'फ':'f', 'ब':'b', 'भ':'bh', 'म':'m',
    'य':'y', 'र':'r', 'ल':'l', 'व':'v', 'श':'sh', 'ष':'sh', 'स':'s', 'ह':'h',
    'ा':'a', 'ि':'i', 'ी':'ee', 'ु':'u', 'ू':'oo', 'े':'e', 'ै':'ai', 'ो':'o', 'ौ':'au',
    'ं':'n', 'ः':'h', '्':'', '़':'', 'ॉ':'o', 'ँ':'n'
}

SYNONYM_MAP = {
    "शक्कर": "sugar", "चीनी": "sugar", "नमक": "salt", "सॉल्ट": "salt", 
    "तेल": "oil", "दूध": "milk", "बिस्किट": "biscuit", "बिस्कुट": "biscuit", 
    "चाय": "tea", "मैगी": "maggi", "मैगी।": "maggi"
}

VERB_CLEANUP = {
    "दे दो": "दे", "कर दो": "कर", "भेज दो": "भेज", "ला दो": "ला", "डाल दो": "डाल", 
    "रख दो": "रख", "बेच दो": "बेच", "का ही है": "आई", "बेच दी": "sold", "बेच दिया": "sold"
}

TEXT_TO_DIGIT = {
    "ढाई सौ": "250", "dhai sau": "250", "पांच सौ": "500", "पाँच सौ": "500", "paanch sau": "500",
    "सौ": "100", "sau": "100", "hundred": "100", "हजार": "1000", "hazaar": "1000", "thousand": "1000",
    "नब्बे": "90", "अस्सी": "80", "assii": "80", "सत्तर": "70", 
    "चौंसठ": "64", "chaunsath": "64", "साठ": "60", 
    "पचास": "50", "pachaas": "50", "पैंतालीस": "45", "चालीस": "40", 
    "पैंतीस": "35", "तीस": "30", "पच्चीस": "25", "बीस": "20", 
    "उन्नीस": "19", "अठारह": "18", "सत्रह": "17", "सोलह": "16", "पंद्रह": "15", 
    "चौदह": "14", "तेरह": "13", "बारह": "12", "ग्यारह": "11", "दस": "10",
    "नौ": "9", "आठ": "8", "सात": "7", "छह": "6", "पांच": "5", "पाँच": "5", "चार": "4", "तीन": "3", "दो": "2", "एक": "1"
}

STRICT_CREDIT_KEYWORDS = ["khaate", "udhaar", "खाते", "उधार", "जमा", "khata", "khaata", "account", "balance", "रुपये", "rupaye", "rupees", "rs", "रुपए"]
RESTOCK_KEYWORDS = ["restock", "add", "मंगवाया", "मंगवाई", "खरीदा", "laaya", "aaya", "aayi", "aai", "aaye", "stock", "buy", "bought", "mangwaya", "kharida", "jod", "daal", "joor", "जोड़", "डाल", "लाया", "आया", "आई", "आयी", "आये"]
STRICT_SELL_KEYWORDS = ["sold", "bech", "diya", "de", "di", "nikal", "sell", "out", "बेच", "दिया", "दे", "दी", "निकाल"]
AMBIGUOUS_SEND = ["भेज", "bhej", "send"]
FILLER_WORDS = ["ke", "mein", "kar", "do", "bhai", "packet", "piece", "ko", "aur", "ka", "ki", "hai", "tha", "pe", "par", "new", "naya", "banao", "create", "the", "of", "to", "item", "को", "में", "कर", "दो", "भाई", "पैकेट", "पीस", "और", "का", "की", "है", "था", "पे", "पर", "नया", "बनाओ", "वाले", "वाली", "kg", "kilo", "gram", "grams", "लीटर", "liter", "ml", "के", "जी", "किलो", "ग्राम"]

def transliterate(text): return "".join(DEVANAGARI_MAP.get(char, char) for char in text)
def clean_string_for_matching(text): return re.sub(r'[^\w\s]', '', re.sub(r'\d+[a-zA-Z]+', '', text.lower())).strip()

def get_db_records(table, column):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f'SELECT {column} FROM {table}')
    records = [row[0] for row in cursor.fetchall()]
    conn.close()
    return records

def extract_number(transcript_lower, default=1):
    normalized = unicodedata.normalize('NFC', transcript_lower)
    normalized_dict = {unicodedata.normalize('NFC', k): v for k, v in TEXT_TO_DIGIT.items()}
    
    words = normalized.split()
    found_numbers = []
    
    for word in words:
        if word in normalized_dict:
            found_numbers.append(int(normalized_dict[word]))
        elif word.isdigit():
            found_numbers.append(int(word))
            
    for hindi_num, val_str in sorted(normalized_dict.items(), key=lambda x: len(x[0]), reverse=True):
        if hindi_num in normalized and not found_numbers:
            found_numbers.append(int(val_str))
            break

    if found_numbers:
        return sum(found_numbers)
        
    digits = re.findall(r'\d+', normalized)
    if digits:
        return int(digits[0])
        
    return default

def extract_unknown_entity(transcript_lower):
    text = transcript_lower
    for phrase in sorted(TEXT_TO_DIGIT.keys(), key=len, reverse=True): text = text.replace(phrase, " ")
    text = re.sub(r'\d+', ' ', text)
    text = re.sub(r'[$.–,—?!\'"]', ' ', text)
    words = text.split()
    ignore_set = set(STRICT_CREDIT_KEYWORDS + RESTOCK_KEYWORDS + STRICT_SELL_KEYWORDS + AMBIGUOUS_SEND + FILLER_WORDS)
    return " ".join([w for w in words if w not in ignore_set]).strip()

def fuzzy_find_best_match(transcript_lower, db_records):
    eng_transcript = transliterate(transcript_lower)
    transcript_words = eng_transcript.split()
    best_match, highest_ratio = None, 0.0
    for record in db_records:
        clean_record = clean_string_for_matching(record)
        record_words = clean_record.split()
        if clean_record in eng_transcript or any(w in eng_transcript for w in record_words if len(w) > 3): 
            return record
        for t_word in transcript_words:
            if len(t_word) < 3: continue
            for r_word in record_words:
                if len(r_word) < 3: continue
                ratio = difflib.SequenceMatcher(None, t_word, r_word).ratio()
                if ratio > 0.65 and ratio > highest_ratio: 
                    highest_ratio = ratio
                    best_match = record
    return best_match

def parse_and_execute(raw_transcript):
    transcript_lower = unicodedata.normalize('NFC', raw_transcript.lower())
    for hindi, eng in SYNONYM_MAP.items(): transcript_lower = transcript_lower.replace(hindi, eng)
    for phrase, rep in VERB_CLEANUP.items(): transcript_lower = transcript_lower.replace(phrase, rep)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    target_customer = fuzzy_find_best_match(transcript_lower, get_db_records('CustomerCredit', 'CustomerName'))
    target_item = fuzzy_find_best_match(transcript_lower, get_db_records('Inventory', 'ItemName'))

    is_credit = any(w in transcript_lower for w in STRICT_CREDIT_KEYWORDS)
    is_restock = any(w in transcript_lower for w in RESTOCK_KEYWORDS)
    is_sell = any(w in transcript_lower for w in STRICT_SELL_KEYWORDS)
    is_send = any(w in transcript_lower for w in AMBIGUOUS_SEND)

    if is_send and not is_credit and not is_restock and not is_sell:
        words = transcript_lower.split()
        if target_customer or "को" in words or "ko" in words: is_credit = True
        else: is_sell = True

    if is_credit:
        amount = extract_number(transcript_lower, default=0)
        if amount == 0: return {"status": "failed", "message": "Could not detect an amount."}
                
        if not target_customer:
            new_name = extract_unknown_entity(transcript_lower)
            if not new_name: return {"status": "failed", "message": "Could not extract a customer name."}
            target_customer = transliterate(new_name).title()
            cursor.execute('INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES (?, ?)', (target_customer, amount))
            message = f"Created new account for {target_customer} with Rs {amount} balance."
        else:
            cursor.execute('SELECT OutstandingBalance FROM CustomerCredit WHERE CustomerName = ?', (target_customer,))
            new_bal = cursor.fetchone()[0] + amount
            cursor.execute('UPDATE CustomerCredit SET OutstandingBalance = ? WHERE CustomerName = ?', (new_bal, target_customer))
            message = f"Added Rs {amount} to {target_customer}. New Balance: Rs {new_bal}."
        
        cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (raw_transcript, amount))
        conn.commit(); conn.close()
        return {"status": "success", "action": "udhaar_added", "message": message}

    elif is_restock:
        quantity = extract_number(transcript_lower, default=1)
        if not target_item:
            new_item = extract_unknown_entity(transcript_lower)
            if not new_item: return {"status": "failed", "message": "Could not extract item name to restock."}
            
            phonetic_name = transliterate(new_item)
            local_name, local_price = normalize_product_locally(phonetic_name)
            
            if local_price > 0:
                cursor.execute('INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)', (local_name, quantity, local_price))
                cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (raw_transcript, 0))
                conn.commit(); conn.close()
                return {"status": "success", "action": "inventory_restocked", "message": f"Added '{local_name}' at ₹{local_price} with {quantity} stock."}
            else:
                conn.close()
                web_name, web_price = search_product_online(phonetic_name)
                return {
                    "status": "pending_confirmation", 
                    "action": "confirm_restock", 
                    "message": f"Internet Search: Found '{web_name}'. Please confirm details.",
                    "draft": {
                        "ItemName": web_name,
                        "Price": web_price,
                        "StockQuantity": quantity,
                        "RawCommand": raw_transcript
                    }
                }
        else:
            cursor.execute('SELECT StockQuantity FROM Inventory WHERE ItemName = ?', (target_item,))
            new_stock = int(cursor.fetchone()[0]) + quantity
            cursor.execute('UPDATE Inventory SET StockQuantity = ? WHERE ItemName = ?', (new_stock, target_item))
            cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (raw_transcript, 0))
            conn.commit(); conn.close()
            return {"status": "success", "action": "inventory_restocked", "message": f"Restocked {quantity} {target_item}. Total stock: {new_stock}."}

    else: # Sales Flow
        if not target_item:
            unknown_name = extract_unknown_entity(transcript_lower)
            if unknown_name:
                phonetic_name = transliterate(unknown_name)
                web_name, web_price = search_product_online(phonetic_name)
                quantity = extract_number(transcript_lower, default=1)
                conn.close()
                return {
                    "status": "pending_confirmation",
                    "action": "confirm_sale",
                    "message": f"Item not found in DB. Retrieved '{web_name}' at ₹{web_price}. Confirm sale?",
                    "draft": {
                        "ItemName": web_name,
                        "Price": web_price,
                        "Quantity": quantity,
                        "RawCommand": raw_transcript
                    }
                }

        if target_item:
            quantity = extract_number(transcript_lower, default=1)
            cursor.execute('SELECT StockQuantity, Price FROM Inventory WHERE ItemName = ?', (target_item,))
            result = cursor.fetchone()
            if result and int(result[0]) >= quantity:
                new_stock = int(result[0]) - quantity
                cursor.execute('UPDATE Inventory SET StockQuantity = ? WHERE ItemName = ?', (new_stock, target_item))
                cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (raw_transcript, result[1] * quantity))
                conn.commit(); conn.close()
                return {"status": "success", "action": "inventory_updated", "message": f"Sold {quantity} {target_item}. Stock left: {new_stock}."}
            elif result:
                conn.close()
                return {"status": "failed", "action": "out_of_stock", "message": f"Not enough {target_item} in stock! Only {result[0]} left."}
                
        conn.close()
        return {"status": "unrecognized", "message": "Could not understand the command or find the item."}