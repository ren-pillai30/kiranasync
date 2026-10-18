import os
import sys
import math
import tempfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import requests

# Explicitly load .env from the root directory
load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../.env'))
load_dotenv() # Fallback

from backend.app.intent_parser import (
    ensure_transactions_schema,
    get_db_records,
    parse_and_execute,
    record_transaction,
)
from backend.app.gemini_understanding import (
    GeminiUnderstandingError,
    understand_command,
)

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

template_dir = get_resource_path('frontend/dist')
static_dir = get_resource_path('frontend/dist/assets')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app)

STT_LANGUAGE_CODES = (
    "bn-IN",
    "en-IN",
    "gu-IN",
    "hi-IN",
    "kn-IN",
    "ml-IN",
    "mr-IN",
    "pa-IN",
    "ta-IN",
    "te-IN",
)


def transcribe_audio(audio_path, language_code="en-IN"):
    """Transcribe audio with Gnani using one of its supported language codes."""
    api_key = os.getenv("GNANI_API_KEY")
    if not api_key:
        print("ERROR: GNANI_API_KEY is missing!")
        return None
    
    try:
        with open(audio_path, "rb") as audio_file:
            response = requests.post(
                "https://api.vachana.ai/stt/v3",
                headers={"X-API-Key-ID": api_key},
                files={"audio_file": (os.path.basename(audio_path), audio_file)},
                data={
                    "language_code": language_code,
                    "format": "transcribe",
                    "itn_native_numerals": str(language_code == "hi-IN").lower(),
                },
                timeout=120,
            )
        response.raise_for_status()
        result = response.json()
        
        if isinstance(result, dict):
            return result.get('transcript', '') or result.get('text', '')
        if isinstance(result, str):
            return result
        return None
    except Exception as e:
        print(f"Gnani STT Exception: {e}")
        return None


def transcribe_audio_candidates(audio_path, language_code):
    if language_code == "auto":
        with ThreadPoolExecutor(max_workers=len(STT_LANGUAGE_CODES)) as executor:
            futures = {
                code: executor.submit(transcribe_audio, audio_path, code)
                for code in STT_LANGUAGE_CODES
            }
            candidates = []
            for code, future in futures.items():
                transcript = future.result()
                if isinstance(transcript, str) and transcript.strip():
                    candidates.append({
                        "language_code": code,
                        "transcript": transcript.strip(),
                    })
            return candidates

    transcript = transcribe_audio(audio_path, language_code=language_code)
    if not isinstance(transcript, str) or not transcript.strip():
        return []
    return [{
        "language_code": language_code,
        "transcript": transcript.strip(),
    }]


@app.route('/api/tts', methods=['POST'])
def synthesize_speech():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "error": "Speech text is required."}), 400

    text = data.get("text")
    language = data.get("language", "en-IN")
    supported_languages = {*STT_LANGUAGE_CODES, "hi-en", "auto"}
    if not isinstance(text, str) or not text.strip() or len(text) > 2000:
        return jsonify({
            "status": "error",
            "error": "Enter speech text with no more than 2000 characters.",
        }), 400
    if not isinstance(language, str) or language not in supported_languages:
        return jsonify({
            "status": "error",
            "error": "Choose a supported Gnani speech language.",
        }), 400

    api_key = os.getenv("GNANI_API_KEY")
    if not api_key:
        return jsonify({
            "status": "error",
            "error": "Gnani is not configured. Set GNANI_API_KEY in the root .env file.",
        }), 503

    try:
        response = requests.post(
            "https://api.vachana.ai/api/v1/tts/inference",
            headers={"X-API-Key-ID": api_key},
            json={
                "text": text.strip(),
                "voice": os.getenv("GNANI_TTS_VOICE", "Shivani"),
                "model": os.getenv("GNANI_TTS_MODEL", "timbre-v3.0"),
                "language": language,
                "speed": 1.0,
                "audio_config": {
                    "sample_rate": 24000,
                    "num_channels": 1,
                    "sample_width": 2,
                    "encoding": "linear_pcm",
                    "container": "wav",
                },
            },
            timeout=45,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        app.logger.warning("Gnani TTS request timed out: %s", exc)
        return jsonify({
            "status": "error",
            "error": "Gnani speech generation timed out. Please try again.",
        }), 504
    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        app.logger.error("Gnani TTS request failed: %s", exc)
        return jsonify({
            "status": "error",
            "error": (
                f"Gnani could not generate speech (HTTP {status_code})."
                if status_code
                else "Gnani could not be reached to generate speech."
            ),
        }), 502

    if not response.content:
        app.logger.error("Gnani TTS returned an empty audio response")
        return jsonify({
            "status": "error",
            "error": "Gnani returned empty speech audio.",
        }), 502

    return send_file(
        BytesIO(response.content),
        mimetype="audio/wav",
        download_name="transaction-confirmation.wav",
    )


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT ItemID, ItemName, StockQuantity, Price FROM Inventory')
    inventory = [{'ItemID': row[0], 'ItemName': row[1], 'StockQuantity': row[2], 'Price': row[3]} for row in cursor.fetchall()]
    
    cursor.execute('SELECT CustomerID, CustomerName, OutstandingBalance FROM CustomerCredit')
    credit = [{'CustomerID': row[0], 'CustomerName': row[1], 'OutstandingBalance': row[2]} for row in cursor.fetchall()]

    conn.close()
    return jsonify({'status': 'success', 'inventory': inventory, 'credit': credit})

@app.route('/api/ledger', methods=['GET'])
def get_transaction_ledger():
    import sqlite3
    from backend.app.intent_parser import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    ensure_transactions_schema(conn)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT rowid, Timestamp, CommandText, TotalAmount,
               TransactionType, EntityName, Quantity
        FROM Transactions
        ORDER BY Timestamp DESC, rowid DESC
    ''')
    transactions = [
        {
            'TxnID': row[0],
            'Timestamp': row[1],
            'CommandText': row[2],
            'TotalAmount': row[3],
            'TransactionType': row[4] or 'Transaction',
            'EntityName': row[5],
            'Quantity': row[6],
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    return jsonify({'status': 'success', 'transactions': transactions})

@app.route('/api/product-lookup', methods=['POST'])
def lookup_product():
    from backend.app.intent_parser import search_product_online

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'error': 'Product name is required.'}), 400
    item_name = data.get('ItemName')
    if not isinstance(item_name, str) or not item_name.strip():
        return jsonify({'status': 'error', 'error': 'Product name is required.'}), 400
    return jsonify({'status': 'success', **search_product_online(item_name.strip())})

@app.route('/api/inventory/confirm-command', methods=['POST'])
def confirm_inventory_command():
    import sqlite3
    from backend.app.intent_parser import DB_PATH

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'error': 'Choose a product variant.'}), 400
    try:
        item_id = int(data.get('ItemID'))
        quantity = int(data.get('Quantity'))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'error': 'Choose a product and valid quantity.'}), 400
    intent = data.get('Intent')
    if intent not in {'sell', 'restock'} or item_id <= 0 or quantity <= 0:
        return jsonify({'status': 'error', 'error': 'Choose a product and valid quantity.'}), 400

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_transactions_schema(conn)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT ItemName, StockQuantity, Price FROM Inventory WHERE ItemID = ?',
            (item_id,),
        )
        item = cursor.fetchone()
        if not item:
            return jsonify({'status': 'error', 'error': 'That inventory item no longer exists.'}), 404

        item_name, stock_quantity, price = item
        if intent == 'sell':
            if int(stock_quantity) < quantity:
                return jsonify({
                    'status': 'error',
                    'error': f'Not enough {item_name} in stock. Only {stock_quantity} left.',
                }), 409
            updated_stock = int(stock_quantity) - quantity
            transaction_type = 'Sale'
            total_amount = float(price) * quantity
            action = 'inventory_updated'
            message = f'Sold {quantity} {item_name}. Stock left: {updated_stock}.'
        else:
            updated_stock = int(stock_quantity) + quantity
            transaction_type = 'Restock'
            total_amount = -float(price) * quantity
            action = 'inventory_restocked'
            message = f'Restocked {quantity} {item_name}. Total stock: {updated_stock}.'

        cursor.execute(
            'UPDATE Inventory SET StockQuantity = ? WHERE ItemID = ?',
            (updated_stock, item_id),
        )
        record_transaction(
            cursor,
            data.get('RawCommand') or f'{intent.title()} {quantity} {item_name}',
            total_amount,
            transaction_type,
            item_name,
            quantity,
        )
        conn.commit()
        return jsonify({
            'status': 'success',
            'database_action': {'status': 'success', 'action': action, 'message': message},
        })
    finally:
        conn.close()

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({'status': 'error', 'error': 'No audio file provided'}), 400

    language_code = request.form.get("language_code", "auto")
    if language_code != "auto" and language_code not in STT_LANGUAGE_CODES:
        return jsonify({
            "status": "error",
            "error": "Choose auto-detect or a supported Gnani language.",
        }), 400

    audio_file = request.files['audio']
    temp_dir = '/tmp' if os.name != 'nt' else os.environ.get('TEMP', '.')
    file_descriptor, audio_path = tempfile.mkstemp(
        prefix="kirana_command_",
        suffix=".wav",
        dir=temp_dir,
    )
    os.close(file_descriptor)
    try:
        audio_file.save(audio_path)
        transcripts = transcribe_audio_candidates(audio_path, language_code)
        if not transcripts:
            return jsonify({
                'status': 'error',
                'error': 'Failed to transcribe audio',
            }), 500

        try:
            interpretation = understand_command(
                transcripts=transcripts,
                inventory=get_db_records("Inventory", "ItemName"),
                customers=get_db_records("CustomerCredit", "CustomerName"),
            )
        except GeminiUnderstandingError as exc:
            return jsonify({
                "status": "error",
                "error": str(exc),
                "transcript": transcripts[0]["transcript"],
            }), 503

        selected_transcript = transcripts[interpretation["transcript_index"]]
        # Execute only after the model's fields have been validated by the parser.
        db_result = parse_and_execute(
            selected_transcript["transcript"],
            interpretation=interpretation,
            preview_only=True,
        )
        if db_result.get("status") in {"pending_review", "pending_selection"}:
            db_result["draft"]["LanguageCode"] = selected_transcript["language_code"]

        return jsonify({
            'status': 'success',
            'transcript': selected_transcript["transcript"],
            'language_code': selected_transcript["language_code"],
            'database_action': db_result
        })
    finally:
        os.remove(audio_path)


@app.route('/api/confirm-transaction', methods=['POST'])
def confirm_transaction():
    import sqlite3
    from backend.app.intent_parser import DB_PATH

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "error": "Transaction details are required.",
        }), 400

    intent = data.get("Intent")
    entity = data.get("EntityName")
    quantity = data.get("Quantity")
    raw_command = data.get("RawCommand")
    if (
        not isinstance(intent, str)
        or intent not in {"sell", "restock", "credit", "inventory_add", "credit_add"}
        or not isinstance(entity, str)
        or not entity.strip()
        or not isinstance(quantity, int)
        or isinstance(quantity, bool)
        or not 0 < quantity <= 2**63 - 1
        or not isinstance(raw_command, str)
    ):
        return jsonify({
            "status": "error",
            "error": "Enter a valid action, item or customer, and positive whole-number amount.",
        }), 400

    if intent in {"inventory_add", "credit_add"}:
        unit_price = data.get("UnitPrice")
        try:
            parsed_unit_price = float(unit_price)
        except (TypeError, ValueError, OverflowError):
            parsed_unit_price = None
        if intent == "inventory_add" and (
            isinstance(unit_price, bool)
            or not isinstance(unit_price, (int, float))
            or parsed_unit_price is None
            or not math.isfinite(parsed_unit_price)
            or not 0 < parsed_unit_price <= 2**63 - 1
        ):
            return jsonify({
                "status": "error",
                "error": "Enter a valid positive item price.",
            }), 400

        connection = sqlite3.connect(DB_PATH)
        try:
            ensure_transactions_schema(connection)
            cursor = connection.cursor()
            if intent == "inventory_add":
                cursor.execute(
                    """
                    INSERT INTO Inventory (ItemName, StockQuantity, Price)
                    VALUES (?, ?, ?)
                    """,
                    (entity.strip(), quantity, parsed_unit_price),
                )
                record_transaction(
                    cursor,
                    raw_command,
                    -parsed_unit_price * quantity,
                    "Restock",
                    entity.strip(),
                    quantity,
                )
                action = "inventory_restocked"
                message = f"Added {quantity} {entity.strip()} to inventory."
            else:
                cursor.execute(
                    """
                    INSERT INTO CustomerCredit (CustomerName, OutstandingBalance)
                    VALUES (?, ?)
                    """,
                    (entity.strip(), quantity),
                )
                record_transaction(
                    cursor,
                    raw_command,
                    quantity,
                    "Credit",
                    entity.strip(),
                )
                action = "udhaar_added"
                message = f"Added Rs {quantity} credit for {entity.strip()}."
            connection.commit()
            return jsonify({
                "status": "success",
                "database_action": {
                    "status": "success",
                    "action": action,
                    "message": message,
                },
            })
        except sqlite3.IntegrityError:
            connection.rollback()
            return jsonify({
                "status": "error",
                "error": "That item or customer already exists. Check the name and try again.",
            }), 409
        finally:
            connection.close()

    result = parse_and_execute(
        raw_command,
        interpretation={
            "action": intent,
            "entity": entity.strip(),
            "quantity": quantity,
        },
    )
    return jsonify({"status": "success", "database_action": result})


@app.route('/api/inventory/add', methods=['POST'])
def add_inventory():
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    ensure_transactions_schema(conn)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)',
                   (data['ItemName'], data['StockQuantity'], data['Price']))
    record_transaction(
        cursor,
        f"Added {data['StockQuantity']} {data['ItemName']} to inventory",
        -float(data['Price']) * float(data['StockQuantity']),
        "Restock",
        data['ItemName'],
        data['StockQuantity'],
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/credit/add', methods=['POST'])
def add_credit():
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    ensure_transactions_schema(conn)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES (?, ?)',
                   (data['CustomerName'], data['Amount']))
    record_transaction(
        cursor,
        f"Added credit for {data['CustomerName']}",
        data['Amount'],
        "Credit",
        data['CustomerName'],
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/inventory/edit', methods=['POST'])
def edit_inventory():
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE Inventory SET ItemName = ? WHERE ItemID = ?', (data['NewItemName'], data['ItemID']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/credit/edit', methods=['POST'])
def edit_credit():
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE CustomerCredit SET CustomerName = ? WHERE CustomerID = ?', (data['NewCustomerName'], data['CustomerID']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/inventory/confirm-restock', methods=['POST'])
def confirm_restock():
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    data = request.json
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'error': 'Product details are required.'}), 400
    item_name = data.get('ItemName')
    raw_items = data.get('Items')
    if raw_items is None:
        raw_items = [{
            'Price': data.get('Price'),
            'Quantity': data.get('StockQuantity'),
        }]
    if not isinstance(raw_items, list) or not raw_items:
        return jsonify({
            'status': 'error',
            'error': 'Choose at least one MRP and stock quantity.',
        }), 400
    if (
        not isinstance(item_name, str)
        or not item_name.strip()
    ):
        return jsonify({
            'status': 'error',
            'error': 'Enter a product name.',
        }), 400

    items = []
    seen_prices = set()
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            return jsonify({'status': 'error', 'error': 'Invalid MRP selection.'}), 400
        try:
            price = float(raw_item.get('Price'))
            raw_quantity = float(raw_item.get('Quantity'))
        except (TypeError, ValueError):
            return jsonify({
                'status': 'error',
                'error': 'Enter a valid MRP and positive whole-number quantity for each product.',
            }), 400
        if (
            not math.isfinite(price)
            or price <= 0
            or not math.isfinite(raw_quantity)
            or not raw_quantity.is_integer()
            or raw_quantity <= 0
        ):
            return jsonify({
                'status': 'error',
                'error': 'Each product needs a valid MRP and positive whole-number quantity.',
            }), 400
        if price in seen_prices:
            return jsonify({
                'status': 'error',
                'error': 'Each selected product must have a different MRP.',
            }), 400
        seen_prices.add(price)
        items.append({'Price': price, 'Quantity': int(raw_quantity)})

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_transactions_schema(conn)
        cursor = conn.cursor()
        for item in items:
            price = item['Price']
            quantity = item['Quantity']
            variant_name = f"{item_name.strip()} (MRP ₹{price:g})"
            cursor.execute(
                'INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)',
                (variant_name, quantity, price),
            )
            record_transaction(
                cursor,
                data.get('RawCommand') or 'Manual Confirmation',
                -price * quantity,
                'Restock',
                variant_name,
                quantity,
            )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({
            'status': 'error',
            'error': 'An inventory product with one of these MRP variants already exists.',
        }), 409
    finally:
        conn.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)