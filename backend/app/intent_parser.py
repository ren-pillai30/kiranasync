
GENERIC_COMMODITY_TERMS = {
    "oil", "tel", "refined", "mustard oil", "sunflower oil", "cooking oil",
    "soap", "sabun", "biscuit", "biscuits", "cookie", "cookies",
    "rice", "chawal", "atta", "flour", "wheat",
    "dal", "daal", "pulse", "pulses",
    "shampoo", "paste", "toothpaste", "brush",
    "chips", "namkeen", "snack", "snacks",
    "milk", "doodh", "curd", "dahi", "ghee", "butter", "paneer",
    "tea", "chai", "coffee",
    "sugar", "cheeni", "shakkar",
    "salt", "namak",
    "masala", "mirch", "haldi", "dhaniya", "spices",
    "noodle", "noodles", "maggi", "pasta",
    "detergent", "powder", "surf",
    "bread", "bun", "toast", "rusk",
    "water", "pani", "soda", "cold drink", "juice",
}

import os
import sys
import sqlite3
import re
import json
import difflib
from number_parser import parse
from backend.app.measurement_utils import (
    extract_measurement,
    extract_all_measurements,
    strip_measurement,
    analyze_measurement_matches,
    check_inventory_item_measurement_mismatch,
)

try:
    from ddgs import DDGS
    from ddgs.exceptions import DDGSException
except ImportError:
    DDGS = None
    DDGSException = None

try:
    from thefuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

def get_writable_db_path():
    """Returns a persistent, writable path for SQLite database."""
    configured_path = os.getenv("KIRANA_DB_PATH")
    if configured_path:
        os.makedirs(os.path.dirname(os.path.abspath(configured_path)), exist_ok=True)
        return configured_path
    if hasattr(sys, '_MEIPASS'):
        app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        target_dir = os.path.join(app_data, 'KiranaSync')
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, 'kirana.db')
    return os.path.join(os.path.abspath("."), 'kirana.db')

DB_PATH = get_writable_db_path()
CATALOG_PATH = os.path.join(os.path.abspath("."), "catalog.json")
MAPPINGS_PATH = os.path.join(os.path.abspath("."), "mappings.json")


def ensure_transactions_schema(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS Transactions (
            TxnID INTEGER PRIMARY KEY AUTOINCREMENT,
            Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            CommandText TEXT,
            TotalAmount REAL
        )
        """
    )
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(Transactions)")
    }
    for column, column_type in (
        ("TransactionType", "TEXT"),
        ("EntityName", "TEXT"),
        ("Quantity", "REAL"),
    ):
        if column not in columns:
            connection.execute(
                f"ALTER TABLE Transactions ADD COLUMN {column} {column_type}"
            )
    from backend.app.db_setup import ensure_archive_schema
    ensure_archive_schema(connection)
    connection.commit()


def record_transaction(
    cursor, command_text, total_amount, transaction_type, entity_name=None, quantity=None
):
    cursor.execute(
        """
        INSERT INTO Transactions
            (CommandText, TotalAmount, TransactionType, EntityName, Quantity)
        VALUES (?, ?, ?, ?, ?)
        """,
        (command_text, total_amount, transaction_type, entity_name, quantity),
    )


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
    """Find a suggested MRP and source for a new inventory item, with measurement awareness."""
    corrected_name = clean_item_name.strip().title()
    requested_meas = extract_measurement(clean_item_name)
    base_product_name = strip_measurement(clean_item_name).strip()

    if not DDGS:
        return {
            "ItemName": corrected_name,
            "Price": None,
            "PriceFound": False,
            "PriceIsMRP": False,
            "SearchStatus": "unavailable",
            "SearchMessage": "Web search is unavailable. Enter the MRP manually.",
            "SpeechMessage": "Web search is unavailable. Enter the MRP manually.",
            "ExactMeasurementFound": None,
            "RequestedMeasurement": requested_meas["display"] if requested_meas else None,
            "AvailableMeasurements": [],
            "SearchResults": [],
        }

    normalized_query_name = re.sub(
        r"\band\b", "&", corrected_name, flags=re.IGNORECASE
    )
    query_names = [corrected_name, normalized_query_name]
    if base_product_name and base_product_name.lower() != corrected_name.lower():
        query_names.append(base_product_name.title())
    ignored_name_tokens = {
        "a", "an", "and", "for", "in", "of", "the", "with",
        "g", "gm", "gram", "grams", "kg", "kgs", "l", "ltr", "ml",
        "pack", "packet", "piece", "pieces", "product", "products",
        "biscuit", "biscuits", "snack", "snacks", "brand",
    }
    brand_tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", corrected_name.lower())
        if token not in ignored_name_tokens and len(token) > 1
    ]
    if brand_tokens:
        normalized_brand = " ".join(brand_tokens)
        query_names.append(normalized_brand)
    queries = list(dict.fromkeys(f"{name} MRP India" for name in query_names))
    try:
        with DDGS() as ddgs:
            results = []
            seen_urls = set()
            for query in queries:
                try:
                    query_results = ddgs.text(query, max_results=5)
                except DDGSException as exc:
                    if str(exc).strip().lower() == "no results found.":
                        continue
                    raise
                for result in query_results:
                    url = result.get("href") or ""
                    if url and url in seen_urls:
                        continue
                    if url:
                        seen_urls.add(url)
                    results.append(result)
                if len(results) >= 10:
                    break
    except Exception as exc:
        print(f"Product MRP search failed: {exc}")
        return {
            "ItemName": corrected_name,
            "Price": None,
            "PriceFound": False,
            "PriceIsMRP": False,
            "SearchStatus": "error",
            "SearchMessage": "Could not retrieve web results. Enter and verify the MRP manually.",
            "SpeechMessage": "Could not retrieve web results. Enter and verify the MRP manually.",
            "ExactMeasurementFound": None,
            "RequestedMeasurement": requested_meas["display"] if requested_meas else None,
            "AvailableMeasurements": [],
            "SearchResults": [],
        }

    search_results = []
    price_options = {}
    mrp_pattern = re.compile(
        r"(?:m\.?\s*r\.?\s*p\.?|maximum\s+retail\s+price)"
        r"\s*(?:is|:|at|-)?\s*(?:₹|rs\.?|inr)?\s*"
        r"(\d{1,5}(?:[,.]\d{1,2})?)",
        re.IGNORECASE,
    )
    price_pattern = re.compile(
        r"price\s*(?:is|:|at|-)?\s*(?:₹|rs\.?|inr)?\s*"
        r"(\d{1,5}(?:[,.]\d{1,2})?)",
        re.IGNORECASE,
    )
    currency_pattern = re.compile(
        r"(?:₹|rs\.?|inr)\s*(\d{1,5}(?:[,.]\d{1,2})?)",
        re.IGNORECASE,
    )
    requested_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", corrected_name.lower())
        if token not in ignored_name_tokens and len(token) > 1
    }
    if not requested_tokens:
        requested_tokens = set(re.findall(r"[a-z0-9]+", corrected_name.lower()))

    for result in results:
        title = (result.get("title") or "").strip()
        body = (result.get("body") or "").strip()
        source = (result.get("href") or "").strip()
        snippet = " ".join(part for part in (title, body) if part)
        if not snippet:
            continue
        result_tokens = set(re.findall(r"[a-z0-9]+", title.lower()))
        if not all(
            any(
                token == result_token
                or (
                    min(len(token), len(result_token)) >= 3
                    and difflib.SequenceMatcher(None, token, result_token).ratio() >= 0.78
                )
                for result_token in result_tokens
            )
            for token in requested_tokens
        ):
            continue

        snippet_measurements = extract_all_measurements(snippet)
        meas_labels = [m["display"] for m in snippet_measurements]

        search_results.append(
            {
                "Title": title,
                "Snippet": body,
                "URL": source,
                "Measurements": meas_labels,
            }
        )

        mrp_matches = mrp_pattern.findall(snippet)
        price_matches = [] if mrp_matches else price_pattern.findall(snippet)
        currency_matches = (
            [] if mrp_matches or price_matches else currency_pattern.findall(snippet)
        )
        matches = [
            *((match, True) for match in mrp_matches),
            *((match, False) for match in price_matches),
            *((match, False) for match in currency_matches),
        ]
        for match, is_mrp in matches:
            try:
                value = float(match.replace(",", ""))
            except ValueError:
                continue
            if value <= 0:
                continue
            option = price_options.setdefault(
                value,
                {
                    "Price": value,
                    "PriceIsMRP": is_mrp,
                    "Sources": [],
                    "Measurements": [],
                },
            )
            option["PriceIsMRP"] = option["PriceIsMRP"] or is_mrp
            option["Sources"].append(
                {"Title": title, "URL": source, "Snippet": body}
            )
            for ml in meas_labels:
                if ml not in option["Measurements"]:
                    option["Measurements"].append(ml)

    sorted_options = sorted(
        price_options.values(),
        key=lambda option: (not option["PriceIsMRP"], option["Price"]),
    )
    price_options_list = [
        {
            **option,
            "Measurement": option["Measurements"][0] if option.get("Measurements") else None,
            "Sources": option["Sources"][:3],
        }
        for option in sorted_options
    ]
    mrp_options = [option for option in price_options_list if option["PriceIsMRP"]]
    selected_options = mrp_options or price_options_list
    price_is_mrp = bool(mrp_options)
    suggested_price = selected_options[0]["Price"] if selected_options else None

    # Measurement match analysis
    cand_texts = [f"{r['Title']} {r.get('Snippet', '')}" for r in search_results]
    meas_analysis = analyze_measurement_matches(clean_item_name, cand_texts)

    if meas_analysis["status"] == "measurement_mismatch":
        search_status = "measurement_mismatch"
        req_disp = meas_analysis["requested_measurement"]
        avail_str = ", ".join(meas_analysis["other_measurements"])
        search_message = (
            f"Exact measurement ({req_disp}) is not available online. "
            f"Other measurements found: {avail_str}. Verify product packaging before selecting."
        )
        speech_message = (
            f"Exact measurement {req_disp} is not available. "
            f"Other sizes like {avail_str} were found."
        )
    elif meas_analysis["status"] == "exact_matched":
        req_disp = meas_analysis["requested_measurement"]
        if mrp_options:
            search_status = "found_mrp"
        elif selected_options:
            search_status = "found_price"
        else:
            search_status = "not_found" if search_results else "no_relevant_results"
        search_message = f"Found exact measurement ({req_disp}) online. Verify it against the product packaging."
        speech_message = f"Found {req_disp} for {corrected_name}."
    else:
        if mrp_options:
            search_status = "found_mrp"
        elif selected_options:
            search_status = "found_price"
        else:
            search_status = "not_found" if search_results else "no_relevant_results"
        search_message = {
            "found_mrp": "An MRP was found online. Verify it against the product packaging.",
            "found_price": "An online price was found, but it may not be the MRP. Verify the product packaging.",
            "found_currency": "An online amount was found, but it may not be the MRP. Verify the product packaging.",
            "not_found": "No reliable MRP was found. Enter and verify it before adding.",
            "no_relevant_results": "No web results matched this product name. Check the name and search again.",
        }[search_status]
        speech_message = search_message

    return {
        "ItemName": corrected_name,
        "Price": suggested_price,
        "PriceFound": suggested_price is not None,
        "PriceIsMRP": price_is_mrp,
        "PriceOptions": price_options_list,
        "SearchStatus": search_status,
        "SearchMessage": search_message,
        "SpeechMessage": speech_message,
        "ExactMeasurementFound": meas_analysis.get("exact_found"),
        "RequestedMeasurement": meas_analysis.get("requested_measurement"),
        "AvailableMeasurements": meas_analysis.get("other_measurements", []),
        "SearchResults": search_results[:3],
    }

def get_db_records(table, column, db_path=None):
    conn = sqlite3.connect(db_path or DB_PATH)
    from backend.app.db_setup import ensure_archive_schema
    ensure_archive_schema(conn)
    cursor = conn.cursor()
    allowed_records = {
        ("Inventory", "ItemName"),
        ("CustomerCredit", "CustomerName"),
    }
    if (table, column) not in allowed_records:
        conn.close()
        raise ValueError("Unsupported catalog table or column.")
    cursor.execute(f'SELECT {column} FROM {table} WHERE IsActive = 1')
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

    normalized_query = ' '.join(normalized_tokens(query_text))
    exact_match = next(
        (
            record for record in db_records
            if ' '.join(normalized_tokens(record)) == normalized_query
        ),
        None,
    )
    if exact_match:
        return exact_match

    meaningful_query_tokens = normalized_tokens(query_text) - GENERIC_COMMODITY_TERMS
    if process and fuzz and not meaningful_query_tokens:
        match = process.extractOne(query_text, db_records, scorer=fuzz.token_set_ratio)
        if match and match[1] >= threshold:
            return match[0]

    if process and fuzz and meaningful_query_tokens:
        best_record, best_score = None, 0
        for record in db_records:
            meaningful_record_tokens = normalized_tokens(record) - GENERIC_COMMODITY_TERMS
            if meaningful_query_tokens.isdisjoint(meaningful_record_tokens):
                continue
            candidate = process.extractOne(query_text, [record], scorer=fuzz.token_set_ratio)
            if candidate and candidate[1] > best_score:
                best_record, best_score = record, candidate[1]
        if best_record and best_score >= threshold:
            return best_record

    query_tokens = normalized_tokens(query_text)
    if not query_tokens:
        return None

    best_record = None
    best_score = 0
    for record in db_records:
        record_tokens = normalized_tokens(record)
        if not record_tokens:
            continue
        if meaningful_query_tokens and meaningful_query_tokens.isdisjoint(
            record_tokens - GENERIC_COMMODITY_TERMS
        ):
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
        if meaningful_query_tokens and meaningful_query_tokens.isdisjoint(
            record_tokens - GENERIC_COMMODITY_TERMS
        ):
            continue
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


def find_unresolved_inventory_variants(cursor, entity_name, raw_transcript):
    cursor.execute(
        "SELECT ItemID, ItemName, StockQuantity, Price FROM Inventory WHERE IsActive = 1"
    )
    inventory = cursor.fetchall()
    if not inventory:
        return []

    # If the user specified a measurement (e.g. "1 kg salt", "1.5 kg salt"), measurement matching takes priority
    req_meas = extract_measurement(entity_name) or extract_measurement(raw_transcript)
    variant_pattern = re.compile(r"\s+\(MRP\s*₹\s*[\d,.]+\)\s*$", re.IGNORECASE)
    base_names = {}
    for row in inventory:
        base_name = variant_pattern.sub("", row[1]).strip()
        base_names.setdefault(base_name.casefold(), []).append(row)

    clean_query = variant_pattern.sub("", entity_name).strip()
    query_lower = clean_query.lower()
    query_tokens = set(re.findall(r'[a-zA-Z0-9]+', query_lower))

    # 1. First check explicit MRP variant ambiguity (e.g. Navratna Oil MRP 400 vs MRP 500)
    base_labels = {
        rows[0][1].casefold(): variant_pattern.sub("", rows[0][1]).strip()
        for rows in base_names.values()
    }
    matched_base = match_entity_with_score(
        clean_query,
        list(base_labels.values()),
        threshold=70,
    )
    if matched_base:
        variants = base_names.get(matched_base.casefold(), [])
        if len(variants) >= 2:
            transcript = raw_transcript.lower()
            explicitly_priced = bool(find_currency_unit(transcript))
            if explicitly_priced:
                spoken_numbers = {
                    float(value.replace(",", ""))
                    for value in re.findall(r"\d+(?:[,.]\d{1,2})?", transcript)
                }
                priced_variants = [row for row in variants if float(row[3]) in spoken_numbers]
                if len(priced_variants) == 1:
                    return []
            return [
                {
                    "ItemID": row[0],
                    "ItemName": row[1],
                    "StockQuantity": row[2],
                    "Price": row[3],
                }
                for row in variants
            ]

    # If the user specified a measurement and it didn't match multiple MRP variants,
    # let measurement compatibility and check_inventory_item_measurement_mismatch handle it.
    if req_meas:
        return []

    # 2. Check for broad generic category queries or multi-item matches (e.g. "oil", "tel", "soap", "biscuit")
    is_generic = (
        query_lower in GENERIC_COMMODITY_TERMS
        or any(token in GENERIC_COMMODITY_TERMS for token in query_tokens)
        or len(query_tokens) <= 1
    )

    matching_rows = []
    for row in inventory:
        item_name_lower = row[1].lower()
        item_tokens = set(re.findall(r'[a-zA-Z0-9]+', item_name_lower))
        meaningful_query_tokens = query_tokens - GENERIC_COMMODITY_TERMS
        meaningful_item_tokens = item_tokens - GENERIC_COMMODITY_TERMS
        if meaningful_query_tokens and meaningful_query_tokens.isdisjoint(meaningful_item_tokens):
            continue
        if query_tokens and (query_tokens <= item_tokens or any(qt in item_tokens for qt in query_tokens if len(qt) >= 3)):
            matching_rows.append(row)

    if matching_rows:
        # If there are 2 or more matching items, always require selection
        if len(matching_rows) >= 2:
            return [
                {
                    "ItemID": row[0],
                    "ItemName": row[1],
                    "StockQuantity": row[2],
                    "Price": row[3],
                }
                for row in matching_rows
            ]
        # If there is exactly 1 matching item, but the user used a broad generic term
        # (e.g. user said 'oil' but item is 'Fortune Sunflower Oil 1L'), require confirmation
        # so the user can choose this variant or choose to add a brand new product
        if len(matching_rows) == 1 and is_generic:
            matched_row = matching_rows[0]
            matched_tokens = set(re.findall(r'[a-zA-Z0-9]+', matched_row[1].lower()))
            # If the inventory item has significant brand tokens missing from query
            if len(matched_tokens - query_tokens) >= 1:
                return [
                    {
                        "ItemID": matched_row[0],
                        "ItemName": matched_row[1],
                        "StockQuantity": matched_row[2],
                        "Price": matched_row[3],
                    }
                ]

    return []


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
    text_string = _strip_trailing_command_words(text_string)
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
    romanized_quantity = _parse_romanized_indian_number(quantity_text)
    if romanized_quantity is not None:
        return romanized_quantity
    return None


_ROMANIZED_NUMBER_WORDS = {
    "zero": 0, "shunya": 0, "sunya": 0,
    "one": 1, "ek": 1, "ick": 1,
    "two": 2, "do": 2,
    "three": 3, "teen": 3, "tin": 3,
    "four": 4, "char": 4, "chaar": 4,
    "five": 5, "panch": 5, "paanch": 5,
    "six": 6, "chah": 6, "chhah": 6, "cheh": 6,
    "seven": 7, "saat": 7,
    "eight": 8, "aath": 8, "ath": 8,
    "nine": 9, "nau": 9, "no": 9,
    "ten": 10, "das": 10, "dus": 10,
    "eleven": 11, "gyarah": 11, "gyaarah": 11,
    "twelve": 12, "barah": 12, "baarah": 12,
    "thirteen": 13, "terah": 13,
    "fourteen": 14, "chaudah": 14, "chaudah": 14,
    "fifteen": 15, "pandrah": 15, "pandra": 15,
    "sixteen": 16, "solah": 16, "solah": 16,
    "seventeen": 17, "satrah": 17, "satara": 17,
    "eighteen": 18, "atharah": 18, "athara": 18,
    "nineteen": 19, "unnis": 19, "unnees": 19, "unnees": 19,
    "twenty": 20, "bees": 20, "bis": 20,
    "twenty one": 21, "ikkis": 21, "ikis": 21,
    "twenty two": 22, "baees": 22, "bais": 22,
    "twenty three": 23, "teees": 23, "teis": 23,
    "twenty four": 24, "chaubees": 24, "chaubis": 24,
    "twenty five": 25, "pachees": 25, "pachis": 25,
    "twenty six": 26, "chhabbees": 26, "chhabbis": 26,
    "twenty seven": 27, "sattais": 27, "sattais": 27,
    "twenty eight": 28, "atthai": 28, "athais": 28,
    "twenty nine": 29, "untees": 29, "untis": 29,
    "thirty": 30, "tees": 30, "tis": 30,
    "thirty one": 31, "iktees": 31, "ikattis": 31,
    "thirty two": 32, "battees": 32, "battis": 32,
    "thirty three": 33, "taintis": 33, "taintees": 33,
    "thirty four": 34, "chauntis": 34, "chauntees": 34,
    "thirty five": 35, "paintis": 35, "paintees": 35,
    "thirty six": 36, "chhattees": 36, "chhatish": 36,
    "thirty seven": 37, "saintees": 37, "saintees": 37,
    "thirty eight": 38, "adtees": 38, "artis": 38,
    "thirty nine": 39, "untaalis": 39, "untalis": 39,
    "forty": 40, "chalis": 40, "chaalis": 40,
    "forty one": 41, "iktalis": 41, "iktyalis": 41,
    "forty two": 42, "bayalis": 42, "bayalis": 42,
    "forty three": 43, "tainatalis": 43, "tentalis": 43,
    "forty four": 44, "chauvaalis": 44, "chavalis": 44,
    "forty five": 45, "paintalis": 45, "pentaalis": 45,
    "forty six": 46, "chhiyaalis": 46, "chiyalis": 46,
    "forty seven": 47, "sainatalis": 47, "santalis": 47,
    "forty eight": 48, "adhiyalis": 48, "arhtalis": 48,
    "forty nine": 49, "unchas": 49,
    "fifty": 50, "pachas": 50, "pachaas": 50,
    "sixty": 60, "saath": 60,
    "sixty one": 61, "iksath": 61, "iksaath": 61,
    "sixty two": 62, "baasath": 62, "basath": 62,
    "sixty three": 63, "tirsath": 63, "tirsaath": 63,
    "sixty four": 64, "chaunsath": 64, "chausaath": 64, "chonsath": 64,
    "sixty five": 65, "paainsath": 65, "painsath": 65,
    "sixty six": 66, "chiyaansath": 66, "chhiyasath": 66,
    "sixty seven": 67, "sarsath": 67, "sarsaath": 67,
    "sixty eight": 68, "arsath": 68, "adhaasath": 68,
    "sixty nine": 69, "unhattar": 69, "unhattar": 69,
    "seventy": 70, "sattar": 70,
    "eighty": 80, "assi": 80,
    "ninety": 90, "nabbe": 90,
    "hundred": 100, "sau": 100,
}


def _strip_trailing_command_words(text_string):
    return re.sub(
        r"\s+(?:bech(?:o|na)?|bik(?:i|na)?|de(?:na)?|dijiye|do)\s*$",
        "",
        text_string.strip(),
        flags=re.IGNORECASE,
    )


def _parse_romanized_indian_number(text_string):
    words = re.findall(r"[a-z]+", text_string.lower())
    while words:
        for size in range(len(words), 0, -1):
            phrase = " ".join(words[:size])
            if phrase in _ROMANIZED_NUMBER_WORDS:
                value = _ROMANIZED_NUMBER_WORDS[phrase]
                if value == 0 and words:
                    continue
                return value
        words.pop(0)
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

def parse_and_execute(raw_transcript, quantity_override=None, interpretation=None, db_path=None):
    target_db = db_path or DB_PATH
    if interpretation is None:
        try:
            english_meaning = translate_to_english(raw_transcript)
        except RuntimeError as exc:
            return {
                "status": "failed",
                "action": "translation_failed",
                "message": str(exc),
            }

    conn = sqlite3.connect(target_db)
    ensure_transactions_schema(conn)
    cursor = conn.cursor()
    db_items = get_db_records('Inventory', 'ItemName', db_path=target_db)
    db_customers = get_db_records('CustomerCredit', 'CustomerName', db_path=target_db)

    from backend.app.services.alias_service import AliasService
    alias_service = AliasService(target_db)

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
        explicit_quantity = extract_explicit_quantity(raw_transcript)
        if explicit_quantity is not None and intent in {"sell", "restock", "credit", "add_product"}:
            quantity_or_amount = explicit_quantity
        INTELLIGENCE_ACTIONS = {
            "query_hisaab", "query_low_stock", "query_stock",
            "query_customer", "repayment", "multi_sell", "assistant_qa",
            "add_customer", "add_product", "remove_product", "remove_customer",
        }
        if intent not in {"sell", "restock", "credit", "unknown"} | INTELLIGENCE_ACTIONS:
            conn.close()
            return {
                "status": "failed",
                "action": "interpretation_invalid",
                "message": "The command could not be safely interpreted. No changes were made.",
            }

        if intent == "query_hisaab":
            from backend.app.services.query_service import QueryService
            qs = QueryService(target_db)
            hisaab = qs.get_today_hisaab()
            conn.close()
            return {
                "status": "success",
                "action": "query_hisaab",
                "message": hisaab["Message"],
                "data": hisaab
            }

        if intent == "query_low_stock":
            from backend.app.services.query_service import QueryService
            qs = QueryService(target_db)
            res = qs.get_low_stock_items()
            conn.close()
            items_text = ", ".join([f"{it['ItemName']} ({it['StockQuantity']} left)" for it in res["items"]]) if res["items"] else "None"
            msg = f"{res['count']} item(s) running low: {items_text}." if res["items"] else "All inventory items have healthy stock levels."
            return {
                "status": "success",
                "action": "query_low_stock",
                "message": msg,
                "items": res["items"]
            }

        if intent == "query_stock":
            from backend.app.services.query_service import QueryService
            qs = QueryService(target_db)
            target = clean_translated_entity or interpretation.get("entity", "")
            res = qs.get_inventory_stock(target)
            conn.close()
            return {
                "status": "success" if res.get("found") else "failed",
                "action": "query_stock",
                "message": res["message"],
                "data": res
            }

        if intent == "query_customer":
            from backend.app.services.query_service import QueryService
            qs = QueryService(target_db)
            target = clean_translated_entity or interpretation.get("entity", "")
            res = qs.get_customer_balance(target)
            conn.close()
            return {
                "status": "success" if res.get("found") else "failed",
                "action": "query_customer",
                "message": res["message"],
                "data": res
            }

        if intent in {"remove_product", "remove_customer"}:
            is_product = intent == "remove_product"
            catalog = db_items if is_product else db_customers
            alias_res = alias_service.resolve_alias(clean_translated_entity or "")
            if alias_res.get("Found") and alias_res.get("EntityType") == (
                "Product" if is_product else "Customer"
            ):
                clean_translated_entity = alias_res["ResolvedName"]
            matched_name = match_entity_with_score(clean_translated_entity, catalog, threshold=70)
            if not matched_name:
                conn.close()
                return {
                    "status": "failed",
                    "action": "entity_not_found",
                    "message": "Could not match an active product or customer. No changes were made.",
                }
            table, id_column, name_column = (
                ("Inventory", "ItemID", "ItemName")
                if is_product
                else ("CustomerCredit", "CustomerID", "CustomerName")
            )
            cursor.execute(
                f"SELECT {id_column}, {name_column}, "
                f"{'StockQuantity' if is_product else 'OutstandingBalance'} "
                f"FROM {table} WHERE {name_column} = ? AND IsActive = 1",
                (matched_name,),
            )
            row = cursor.fetchone()
            if not row:
                conn.close()
                return {
                    "status": "failed",
                    "action": "entity_not_found",
                    "message": "That product or customer is no longer active. No changes were made.",
                }
            if not is_product and float(row[2] or 0) < 1:
                conn.close()
                from backend.app.services.entity_service import EntityService
                return EntityService(target_db).archive_customer(
                    row[0],
                    reason=interpretation.get("reason", ""),
                    raw_command=raw_transcript,
                )
            conn.close()
            return {
                "status": "pending_confirmation",
                "action": "archive_entity",
                "message": f"Confirm removal of {row[1]} from the active {'inventory' if is_product else 'udhaar list'}.",
                "draft": {
                    "EntityType": "Product" if is_product else "Customer",
                    "EntityID": row[0],
                    "EntityName": row[1],
                    "QuantityOrBalance": row[2],
                    "Reason": interpretation.get("reason", ""),
                    "RawCommand": raw_transcript,
                },
            }

        if intent == "add_customer":
            if not isinstance(clean_translated_entity, str) or not clean_translated_entity.strip():
                conn.close()
                return {
                    "status": "failed",
                    "action": "entity_unrecognized",
                    "message": "Could not identify a customer to add. No changes were made.",
                }
            customer_name = clean_translated_entity.strip()
            if match_entity_with_score(customer_name, db_customers, threshold=90):
                conn.close()
                return {
                    "status": "failed",
                    "action": "customer_already_exists",
                    "message": f"{customer_name} is already in the active customer list.",
                }
            cursor.execute(
                "SELECT CustomerID FROM CustomerCredit WHERE lower(CustomerName) = lower(?) AND IsActive = 0",
                (customer_name,),
            )
            archived_customer = cursor.fetchone()
            if archived_customer:
                cursor.execute(
                    "UPDATE CustomerCredit SET IsActive = 1 WHERE CustomerID = ?",
                    (archived_customer[0],),
                )
            else:
                cursor.execute(
                    "INSERT INTO CustomerCredit (CustomerName, OutstandingBalance, IsActive) VALUES (?, 0, 1)",
                    (customer_name,),
                )
            conn.commit()
            conn.close()
            return {
                "status": "success",
                "action": "customer_added",
                "message": f"Added {customer_name} to the active customer list.",
            }

        if intent == "repayment":
            from backend.app.services.transaction_service import TransactionService
            cust_name = clean_translated_entity or interpretation.get("entity", "")
            amount = quantity_or_amount or 0
            if amount <= 0:
                conn.close()
                return {"status": "failed", "action": "repayment_failed", "message": "Please specify a positive repayment amount."}
            try:
                res = TransactionService.commit_repayment(conn, {"CustomerName": cust_name, "Amount": amount, "RawCommand": raw_transcript}, None)
                conn.commit()
                conn.close()
                return {
                    "status": "success",
                    "action": "repayment_recorded",
                    "message": res["Message"],
                    "data": res
                }
            except Exception as e:
                conn.close()
                return {"status": "failed", "action": "repayment_failed", "message": str(e)}

        if intent == "multi_sell":
            items = interpretation.get("items", [])
            if not items:
                conn.close()
                return {"status": "failed", "action": "multi_sell_empty", "message": "No items found in multi-item sale command."}
            from backend.app.services.transaction_service import TransactionService
            sold_summary = []
            errors = []
            for item in items:
                prod_name = item.get("entity", "").strip()
                qty = int(item.get("quantity", 1))
                matched_item = match_entity_with_score(prod_name, db_items, threshold=60)
                if not matched_item:
                    errors.append(f"'{prod_name}' not found")
                    continue
                meas_mismatch = check_inventory_item_measurement_mismatch(cursor, prod_name, matched_item)
                if meas_mismatch:
                    errors.append(f"{prod_name}: {meas_mismatch['message']}")
                    continue
                cursor.execute("SELECT ItemID FROM Inventory WHERE ItemName = ?", (matched_item,))
                row = cursor.fetchone()
                if not row:
                    errors.append(f"'{matched_item}' not found")
                    continue
                try:
                    res = TransactionService.commit_sale(conn, {"ItemID": row[0], "Quantity": qty, "RawCommand": raw_transcript}, None)
                    sold_summary.append(f"{qty}x {matched_item}")
                except Exception as e:
                    errors.append(f"{matched_item}: {str(e)}")
            conn.commit()
            conn.close()
            if sold_summary:
                msg = f"Multi-item sale recorded: {', '.join(sold_summary)}."
                if errors:
                    msg += f" (Notice: {'; '.join(errors)})"
                return {"status": "success", "action": "multi_sale_completed", "message": msg, "sold": sold_summary}
            return {"status": "failed", "action": "multi_sale_failed", "message": "; ".join(errors) or "Could not process items."}

        if intent == "assistant_qa":
            conn.close()
            reply = interpretation.get("spoken_response") or "I am your KiranaSync shop assistant. Ask me to sell, restock, check hisaab, check stock, or check customer balances."
            return {
                "status": "success",
                "action": "assistant_qa",
                "message": reply
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
        alias_res = alias_service.resolve_alias(clean_translated_entity)
        if alias_res.get("Ambiguous"):
            conn.close()
            return {
                "status": "pending_clarification",
                "action": "ambiguous_alias",
                "message": alias_res.get("Message", "Ambiguous alias found. Clarification needed."),
                "candidates": alias_res.get("Candidates", []),
            }
        if alias_res.get("Found"):
            resolved_target = alias_res["ResolvedName"]
            if alias_res["EntityType"] == "Product" and intent in {"sell", "restock", "add_product"}:
                clean_translated_entity = resolved_target
            elif alias_res["EntityType"] == "Customer" and intent in {"credit", "add_customer"}:
                clean_translated_entity = resolved_target

        target_item = (
            match_entity_with_score(clean_translated_entity, db_items, threshold=70)
            if intent in {"sell", "restock", "add_product"}
            else None
        )
        target_customer = (
            match_entity_with_score(clean_translated_entity, db_customers, threshold=70)
            if intent in {"credit", "add_customer"}
            else None
        )
    else:
        # Preserve the local parser path for callers that do not provide an interpretation.
        clean_translated_entity = isolate_clean_entity(english_meaning)
        alias_res = alias_service.resolve_alias(clean_translated_entity)
        if alias_res.get("Ambiguous"):
            conn.close()
            return {
                "status": "pending_clarification",
                "action": "ambiguous_alias",
                "message": alias_res.get("Message", "Ambiguous alias found. Clarification needed."),
                "candidates": alias_res.get("Candidates", []),
            }
        if alias_res.get("Found"):
            clean_translated_entity = alias_res["ResolvedName"]

        target_item = match_entity_with_score(clean_translated_entity, db_items, threshold=70)
        target_customer = match_entity_with_score(clean_translated_entity, db_customers, threshold=70)
        intent = determine_intent(english_meaning)
        quantity_or_amount = (
            quantity_override
            if quantity_override is not None
            else extract_quantity(english_meaning)
        )

    if intent == "add_product" and target_item:
        query_lower = clean_translated_entity.strip().lower()
        query_tokens = set(re.findall(r'[a-zA-Z0-9]+', query_lower))
        is_generic = (
            query_lower in GENERIC_COMMODITY_TERMS
            or any(token in GENERIC_COMMODITY_TERMS for token in query_tokens)
            or len(query_tokens) <= 1
        )
        if not is_generic and target_item.lower().strip() == clean_translated_entity.lower().strip():
            conn.close()
            return {
                "status": "failed",
                "action": "product_already_exists",
                "message": f"{target_item} is already active in inventory. Use a restock command to add stock.",
            }

    if quantity_or_amount is None:
        conn.close()
        return {
            "status": "failed",
            "action": "quantity_unrecognized",
            "message": "Could not recognize the quantity. Please repeat the amount clearly.",
        }

    final_unknown_entity = clean_translated_entity

    if intent in {"sell", "restock", "add_product"} and target_item:
        variants = find_unresolved_inventory_variants(
            cursor, clean_translated_entity, raw_transcript
        )
        if variants:
            conn.close()
            req_m = extract_measurement(clean_translated_entity) or extract_measurement(raw_transcript)
            meas_analysis = (
                analyze_measurement_matches(req_m["display"], [v["ItemName"] for v in variants])
                if req_m
                else {"status": "none"}
            )
            if meas_analysis.get("status") == "measurement_mismatch":
                req_disp = meas_analysis["requested_measurement"]
                avail_str = ", ".join(meas_analysis["other_measurements"])
                msg = f"Exact measurement ({req_disp}) is not in stock. Other sizes ({avail_str}) exist. Choose a variant."
                speech = f"Exact measurement {req_disp} is not available. Other sizes like {avail_str} exist."
            else:
                msg = "More than one inventory variant matches. Choose the exact product before changing stock."
                speech = msg

            return {
                "status": "pending_selection",
                "action": "select_inventory_item",
                "message": msg,
                "speech_message": speech,
                "draft": {
                    "Intent": intent,
                    "Quantity": quantity_or_amount,
                    "RawCommand": raw_transcript,
                    "EntityName": final_unknown_entity,
                    "Candidates": variants,
                    "AllowNewProduct": True,
                    "RequestedMeasurement": meas_analysis.get("requested_measurement"),
                    "AvailableMeasurements": meas_analysis.get("other_measurements", []),
                    "MeasurementMismatch": meas_analysis.get("status") == "measurement_mismatch",
                },
            }

    # Verify measurement compatibility if measurement mentioned in voice command
    item_to_check = target_item or (
        match_entity_with_score(raw_transcript, db_items, threshold=70)
        if extract_measurement(raw_transcript)
        else None
    )
    if item_to_check:
        meas_mismatch = check_inventory_item_measurement_mismatch(
            cursor,
            f"{clean_translated_entity} {raw_transcript}",
            item_to_check,
        )
        if meas_mismatch:
            conn.close()
            return {
                "status": "failed",
                "action": "measurement_mismatch",
                "message": meas_mismatch["message"],
                "speech_message": meas_mismatch["speech_message"],
                "requested_measurement": meas_mismatch["requested_measurement"],
                "available_measurements": meas_mismatch["available_measurements"],
            }

    # --- EXECUTE TRANSACTIONS ---
    if intent == 'credit' or target_customer:
        amount = quantity_or_amount
        conn.close()
        customer_name = target_customer or final_unknown_entity or clean_translated_entity
        return {
            "status": "pending_confirmation",
            "action": "confirm_credit",
            "message": f"Confirm adding Rs {amount:g} to {customer_name}.",
            "draft": {
                "Intent": "credit",
                "CustomerName": customer_name,
                "Amount": amount,
                "RawCommand": raw_transcript,
            },
        }

    elif intent in {'restock', 'add_product'}:
        if target_item:
            cursor.execute(
                'SELECT ItemID, StockQuantity, Price FROM Inventory WHERE ItemName = ?',
                (target_item,),
            )
            row = cursor.fetchone()
            conn.close()
            new_stock = int(row[1]) + quantity_or_amount if row else quantity_or_amount
            return {
                "status": "pending_confirmation",
                "action": "confirm_restock",
                "message": f"Confirm restocking {quantity_or_amount} {target_item}. Total stock after restock: {new_stock}.",
                "draft": {
                    "Intent": "restock",
                    "ItemID": row[0] if row else None,
                    "ItemName": target_item,
                    "Quantity": quantity_or_amount,
                    "CurrentStock": int(row[1]) if row else 0,
                    "RawCommand": raw_transcript,
                },
            }
        else:
            conn.close()
            return {
                "status": "pending_confirmation",
                "action": "confirm_restock",
                "message": f"Confirm adding {quantity_or_amount} units of new product {final_unknown_entity}.",
                "draft": {
                    "ItemName": final_unknown_entity,
                    "StockQuantity": quantity_or_amount,
                    "Price": None,
                    "PriceFound": False,
                    "PriceOptions": [],
                    "SearchStatus": "idle",
                    "RawCommand": raw_transcript,
                }
            }

    else:
        if target_item:
            cursor.execute('SELECT ItemID, StockQuantity, Price FROM Inventory WHERE ItemName = ?', (target_item,))
            result = cursor.fetchone()
            if result and int(result[1]) >= quantity_or_amount:
                conn.close()
                new_stock = int(result[1]) - quantity_or_amount
                return {
                    "status": "pending_confirmation",
                    "action": "confirm_sale",
                    "message": f"Confirm selling {quantity_or_amount} {target_item}. Stock left after sale: {new_stock}.",
                    "draft": {
                        "Intent": "sell",
                        "ItemID": result[0],
                        "ItemName": target_item,
                        "Quantity": quantity_or_amount,
                        "CurrentStock": int(result[1]),
                        "RawCommand": raw_transcript,
                    },
                }
            elif result:
                conn.close()
                return {"status": "failed", "action": "out_of_stock", "message": f"Not enough {target_item} in stock! Only {result[1]} left."}
        else:
            conn.close()
            return {
                "status": "failed",
                "action": "item_not_found",
                "message": f"Could not match '{final_unknown_entity}' to an inventory item. No stock was changed.",
            }