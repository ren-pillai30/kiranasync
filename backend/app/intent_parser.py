import os
import sys
import sqlite3
import re
import difflib

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

DB_PATH = get_resource_path('kirana.db')

# --- TRANSLITERATION, SYNONYMS & GRAMMAR MAPS ---
DEVANAGARI_MAP = {
    'अ':'a', 'आ':'aa', 'इ':'i', 'ई':'ee', 'उ':'u', 'ऊ':'oo', 'ए':'e', 'ऐ':'ai', 'ओ':'o', 'औ':'au',
    'क':'k', 'ख':'kh', 'ग':'g', 'घ':'gh', 'च':'ch', 'छ':'chh', 'ज':'j', 'झ':'jh',
    'ट':'t', 'ठ':'th', 'ड':'d', 'ढ':'dh', 'त':'t', 'थ':'th', 'द':'d', 'ध':'dh', 'न':'n',
    'प':'p', 'फ':'f', 'ब':'b', 'भ':'bh', 'म':'m',
    'य':'y', 'र':'r', 'ल':'l', 'व':'v', 'श':'sh', 'ष':'sh', 'स':'s', 'ह':'h',
    'ा':'a', 'ि':'i', 'ी':'ee', 'ु':'u', 'ू':'oo', 'े':'e', 'ै':'ai', 'ो':'o', 'ौ':'au',
    'ं':'n', 'ः':'h', '्':'', '़':'', 'ॉ':'o', 'ँ':'n'
}

# Translates local Hindi terms that have zero phonetic overlap with their English database entries
SYNONYM_MAP = {
    "शक्कर": "sugar", "चीनी": "sugar", "शुगर": "sugar",
    "नमक": "salt", "सॉल्ट": "salt", "साल्ट": "salt",
    "तेल": "oil", "ऑयल": "oil",
    "दूध": "milk", "पानी": "water", "चावल": "rice", "आटा": "atta"
}

# Fixed to include "बेच दो" to prevent "दो" from acting as the number 2
VERB_CLEANUP = {
    "दे दो": "दे", "कर दो": "कर", "भेज दो": "भेज", "ला दो": "ला", "डाल दो": "डाल", "रख दो": "रख", "बेच दो": "बेच",
    "de do": "de", "kar do": "kar", "bhej do": "bhej", "la do": "la", "daal do": "daal", "aayi hai": "aayi", "आई है": "आई"
}

TEXT_TO_DIGIT = {
    "ढाई सौ": "250", "dhai sau": "250", "पांच सौ": "500", "paanch sau": "500",
    "सौ": "100", "sau": "100", "hundred": "100", "हजार": "1000", "hazaar": "1000", "thousand": "1000",
    "निन्यानवे": "99", "ninety nine": "99", "अट्ठानवे": "98", "ninety eight": "98", "संतानवे": "97", "ninety seven": "97", "छियानवे": "96", "ninety six": "96", "पचानवे": "95", "ninety five": "95", "चौरानवे": "94", "ninety four": "94", "तिरानवे": "93", "ninety three": "93", "बानवे": "92", "ninety two": "92", "इक्यानवे": "91", "ninety one": "91", "नब्बे": "90", "ninety": "90",
    "नवासी": "89", "eighty nine": "89", "अट्ठासी": "88", "eighty eight": "88", "सत्तासी": "87", "eighty seven": "87", "छियासी": "86", "eighty six": "86", "पचासी": "85", "eighty five": "85", "चौरासी": "84", "eighty four": "84", "तिरासी": "83", "eighty three": "83", "बयासी": "82", "eighty two": "82", "इक्यासी": "81", "eighty one": "81", "अस्सी": "80", "eighty": "80",
    "उन्नासी": "79", "seventy nine": "79", "अठहत्तर": "78", "seventy eight": "78", "सतहत्तर": "77", "seventy seven": "77", "छिहत्तर": "76", "seventy six": "76", "पचहत्तर": "75", "seventy five": "75", "चौहत्तर": "74", "seventy four": "74", "तिहत्तर": "73", "seventy three": "73", "बहत्तर": "72", "seventy two": "72", "इकहत्तर": "71", "seventy one": "71", "सत्तर": "70", "seventy": "70",
    "उनहत्तर": "69", "sixty nine": "69", "अड़सठ": "68", "sixty eight": "68", "सड़सठ": "67", "sixty seven": "67", "छियासठ": "66", "sixty six": "66", "पैंसठ": "65", "sixty five": "65", "चौंसठ": "64", "चौसठ": "64", "sixty four": "64", "तिरेसठ": "63", "sixty three": "63", "बासठ": "62", "sixty two": "62", "इकसठ": "61", "sixty one": "61", "साठ": "60", "sixty": "60",
    "उनसठ": "59", "fifty nine": "59", "अट्ठावन": "58", "fifty eight": "58", "सत्तावन": "57", "fifty seven": "57", "छप्पन": "56", "fifty six": "56", "पचपन": "55", "fifty five": "55", "चौवन": "54", "fifty four": "54", "तिरेपन": "53", "fifty three": "53", "बावन": "52", "fifty two": "52", "इक्यावन": "51", "fifty one": "51", "पचास": "50", "fifty": "50",
    "उनचास": "49", "forty nine": "49", "अड़तालीस": "48", "forty eight": "48", "सैंतालीस": "47", "forty seven": "47", "छियालीस": "46", "forty six": "46", "पैंतालीस": "45", "forty five": "45", "चवालीस": "44", "forty four": "44", "तैंतालीस": "43", "forty three": "43", "बयालीस": "42", "forty two": "42", "इकतालीस": "41", "forty one": "41", "चालीस": "40", "forty": "40",
    "उनतालीस": "39", "thirty nine": "39", "अड़तीस": "38", "thirty eight": "38", "सैंतीस": "37", "thirty seven": "37", "छत्तीस": "36", "thirty six": "36", "पैंतीस": "35", "thirty five": "35", "चौंतीस": "34", "thirty four": "34", "तैंतीस": "33", "thirty three": "33", "बत्तीस": "32", "thirty two": "32", "इकतीस": "31", "thirty one": "31", "तीस": "30", "thirty": "30",
    "उनतीस": "29", "twenty nine": "29", "अट्ठाईस": "28", "twenty eight": "28", "सत्ताईस": "27", "twenty seven": "27", "छब्बीस": "26", "twenty six": "26", "पच्चीस": "25", "twenty five": "25", "चौबीस": "24", "twenty four": "24", "तेईस": "23", "twenty three": "23", "बाईस": "22", "twenty two": "22", "इक्कीस": "21", "twenty one": "21", "बीस": "20", "twenty": "20",
    "उन्नीस": "19", "nineteen": "19", "अठारह": "18", "eighteen": "18", "सत्रह": "17", "seventeen": "17", "सोलह": "16", "sixteen": "16", "पंद्रह": "15", "fifteen": "15", "चौदह": "14", "fourteen": "14", "तेरह": "13", "thirteen": "13", "बारह": "12", "twelve": "12", "ग्यारह": "11", "eleven": "11", "दस": "10", "ten": "10", "नौ": "9", "nine": "9", "आठ": "8", "eight": "8", "सात": "7", "seven": "7", "छह": "6", "six": "6", "पांच": "5", "five": "5", "चार": "4", "four": "4", "तीन": "3", "three": "3", "दो": "2", "two": "2", "एक": "1", "one": "1"
}

STRICT_CREDIT_KEYWORDS = ["khaate", "udhaar", "खाते", "उधार", "जमा", "khata", "khaata", "account", "balance", "रुपये", "rupaye", "rupees", "rs", "रुपए"]
RESTOCK_KEYWORDS = ["restock", "add", "मंगवाया", "मंगवाई", "खरीदा", "laaya", "aaya", "aayi", "aai", "stock", "buy", "bought", "mangwaya", "kharida", "jod", "daal", "joor", "जोड़", "डाल", "लाया", "आया", "आई"]
STRICT_SELL_KEYWORDS = ["sold", "bech", "diya", "de", "di", "nikal", "sell", "out", "बेच", "दिया", "दे", "दी", "निकाल"]
AMBIGUOUS_SEND = ["भेज", "bhej", "send"]
FILLER_WORDS = ["ke", "mein", "kar", "do", "bhai", "packet", "piece", "ko", "aur", "ka", "ki", "hai", "tha", "pe", "par", "new", "naya", "banao", "create", "the", "of", "to", "item", "को", "में", "कर", "दो", "भाई", "पैकेट", "पीस", "और", "का", "की", "है", "था", "पे", "पर", "नया", "बनाओ", "वाले", "वाली", "kg", "kilo", "gram", "grams", "लीटर", "liter", "ml", "के", "जी", "किलो", "ग्राम"]

def transliterate(text):
    return "".join(DEVANAGARI_MAP.get(char, char) for char in text)

def get_db_records(table, column):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f'SELECT {column} FROM {table}')
    records = [row[0] for row in cursor.fetchall()]
    conn.close()
    return records

def extract_number(transcript_lower, default=1):
    processed_text = transcript_lower
    for word in sorted(TEXT_TO_DIGIT.keys(), key=len, reverse=True):
        processed_text = processed_text.replace(word, TEXT_TO_DIGIT[word])
        
    digits = re.findall(r'\d+', processed_text)
    if not digits:
        return default
        
    total = 0
    current = 0
    for num_str in digits:
        val = int(num_str)
        if val >= 100:
            if current == 0:
                current = 1
            total += current * val
            current = 0
        else:
            current += val
            
    total += current
    return total if total > 0 else default

def clean_string_for_matching(text):
    clean = re.sub(r'\d+[a-zA-Z]+', '', text.lower())
    clean = re.sub(r'[^\w\s]', '', clean).strip()
    return clean

def extract_unknown_entity(transcript_lower):
    text = transcript_lower
    for phrase in sorted(TEXT_TO_DIGIT.keys(), key=len, reverse=True):
        text = text.replace(phrase, " ")
    text = re.sub(r'\d+', ' ', text)
    text = re.sub(r'[।.,?!\'"]', ' ', text)
    
    words = text.split()
    ignore_set = set(STRICT_CREDIT_KEYWORDS + RESTOCK_KEYWORDS + STRICT_SELL_KEYWORDS + AMBIGUOUS_SEND + FILLER_WORDS)
    final_words = [w for w in words if w not in ignore_set]
    return " ".join(final_words).strip()

def fuzzy_find_best_match(transcript_lower, db_records):
    eng_transcript = transliterate(transcript_lower)
    transcript_words = eng_transcript.split()
    best_match = None
    highest_ratio = 0.0
    
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
    transcript_lower = raw_transcript.lower()
    
    # 1. Translate true semantic Hindi words to English for database matching
    for hindi, eng in SYNONYM_MAP.items():
        transcript_lower = transcript_lower.replace(hindi, eng)
        
    # 2. Sanitize verb grammar to protect number parsing
    for phrase, replacement in VERB_CLEANUP.items():
        transcript_lower = transcript_lower.replace(phrase, replacement)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    customers = get_db_records('CustomerCredit', 'CustomerName')
    items = get_db_records('Inventory', 'ItemName')

    target_customer = fuzzy_find_best_match(transcript_lower, customers)
    target_item = fuzzy_find_best_match(transcript_lower, items)

    is_credit = any(w in transcript_lower for w in STRICT_CREDIT_KEYWORDS)
    is_restock = any(w in transcript_lower for w in RESTOCK_KEYWORDS)
    is_sell = any(w in transcript_lower for w in STRICT_SELL_KEYWORDS)
    is_send = any(w in transcript_lower for w in AMBIGUOUS_SEND)

    # CONTEXT-AWARE ROUTER
    if is_send and not is_credit and not is_restock and not is_sell:
        words = transcript_lower.split()
        if target_customer or "को" in words or "ko" in words:
            is_credit = True
        else:
            is_sell = True

    # --- 1. DYNAMIC CREDIT / UDHAAR INTENT ---
    if is_credit:
        amount = extract_number(transcript_lower, default=0)
        if amount == 0:
            return {"status": "failed", "message": "Could not detect an amount."}
                
        if not target_customer:
            new_name = extract_unknown_entity(transcript_lower)
            if not new_name:
                return {"status": "failed", "message": "Could not extract a customer name."}
            target_customer = transliterate(new_name).title()
            cursor.execute('INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES (?, ?)', (target_customer, amount))
            message = f"Created new account for {target_customer} with Rs {amount} balance."
        else:
            cursor.execute('SELECT OutstandingBalance FROM CustomerCredit WHERE CustomerName = ?', (target_customer,))
            current_bal = cursor.fetchone()[0]
            new_bal = current_bal + amount
            cursor.execute('UPDATE CustomerCredit SET OutstandingBalance = ? WHERE CustomerName = ?', (new_bal, target_customer))
            message = f"Added Rs {amount} to {target_customer}. New Balance: Rs {new_bal}."
        
        cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (raw_transcript, amount))
        conn.commit()
        conn.close()
        return {"status": "success", "action": "udhaar_added", "message": message}

    # --- 2. RESTOCK / ADD INVENTORY INTENT ---
    elif is_restock:
        quantity = extract_number(transcript_lower, default=1)
        if not target_item:
            new_item = extract_unknown_entity(transcript_lower)
            if not new_item:
                return {"status": "failed", "message": "Could not extract item name to restock."}
            target_item = transliterate(new_item).title()
            cursor.execute('INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)', (target_item, quantity, 0))
            message = f"Added new item '{target_item}' with {quantity} stock."
        else:
            cursor.execute('SELECT StockQuantity FROM Inventory WHERE ItemName = ?', (target_item,))
            result = cursor.fetchone()
            if result:
                current_stock = int(result[0])
                new_stock = current_stock + quantity
                cursor.execute('UPDATE Inventory SET StockQuantity = ? WHERE ItemName = ?', (new_stock, target_item))
                message = f"Restocked {quantity} {target_item}. Total stock: {new_stock}."
            else:
                return {"status": "failed", "message": "Database error: Item not found."}
            
        cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (raw_transcript, 0))
        conn.commit()
        conn.close()
        return {"status": "success", "action": "inventory_restocked", "message": message}

    # --- 3. SELL INVENTORY INTENT (Default) ---
    else:
        if target_item:
            quantity = extract_number(transcript_lower, default=1)
            cursor.execute('SELECT StockQuantity, Price FROM Inventory WHERE ItemName = ?', (target_item,))
            result = cursor.fetchone()
            
            if result and int(result[0]) >= quantity:
                new_stock = int(result[0]) - quantity
                total_price = result[1] * quantity
                cursor.execute('UPDATE Inventory SET StockQuantity = ? WHERE ItemName = ?', (new_stock, target_item))
                cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', (raw_transcript, total_price))
                conn.commit()
                conn.close()
                return {"status": "success", "action": "inventory_updated", "message": f"Sold {quantity} {target_item}. Stock left: {new_stock}."}
            elif result and int(result[0]) < quantity:
                conn.close()
                return {"status": "failed", "action": "out_of_stock", "message": f"Not enough {target_item} in stock! Only {result[0]} left."}
                
        return {"status": "unrecognized", "message": "Could not understand the command or find the item."}