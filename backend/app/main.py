import os
import sys
import math
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import requests

# Explicitly load .env from the root directory
load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../.env'))
load_dotenv() # Fallback

from backend.app.intent_parser import (
    extract_explicit_quantity,
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

from backend.app.providers.gnani_stt import GnaniSTTProvider
from backend.app.providers.gnani_tts import GnaniTTSProvider

stt_provider = GnaniSTTProvider()
tts_provider = GnaniTTSProvider()

def transcribe_audio(audio_path, language_code="hi-IN"):
    """Transcribe audio with Gnani (hi-IN natively supports Hindi and Hinglish)."""
    return stt_provider.transcribe(
        audio_path,
        language_code=language_code,
        native_numerals=(language_code == "hi-IN")
    )

@app.route('/api/voice/synthesize', methods=['POST'])
def synthesize_voice():
    """Generates audio bytes from server-verified text using Gnani Timbre TTS."""
    from flask import Response
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    language_code = data.get("language_code", "hi-IN")

    if not text:
        return jsonify({'status': 'error', 'error': 'Text is required'}), 400

    try:
        audio_bytes, content_type = tts_provider.synthesize(text, language_code=language_code)
        return Response(audio_bytes, mimetype=content_type)
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 503

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

@app.route('/api/analytics/hisaab', methods=['GET'])
def get_hisaab_summary():
    from backend.app.intent_parser import DB_PATH
    from backend.app.services.query_service import QueryService
    service = QueryService(DB_PATH)
    return jsonify(service.get_today_hisaab())

@app.route('/api/analytics/low-stock', methods=['GET'])
def get_low_stock():
    from backend.app.intent_parser import DB_PATH
    from backend.app.services.query_service import QueryService
    service = QueryService(DB_PATH)
    return jsonify(service.get_low_stock_items())

@app.route('/api/query/balance', methods=['GET'])
def get_balance_query():
    from backend.app.intent_parser import DB_PATH
    from backend.app.services.query_service import QueryService
    customer = request.args.get('customer', '')
    if not customer:
        return jsonify({'status': 'error', 'error': 'Customer name required'}), 400
    service = QueryService(DB_PATH)
    return jsonify(service.get_customer_balance(customer))

@app.route('/api/aliases', methods=['GET', 'POST'])
def manage_aliases():
    from backend.app.intent_parser import DB_PATH
    from backend.app.services.alias_service import AliasService
    service = AliasService(DB_PATH)
    if request.method == 'GET':
        return jsonify({'status': 'success', 'aliases': service.list_aliases()})
    
    data = request.get_json(silent=True) or {}
    entity_type = data.get("EntityType")
    entity_id = data.get("EntityID")
    resolved_name = data.get("ResolvedName")
    spoken_alias = data.get("SpokenAlias")

    if not (entity_type and entity_id and resolved_name and spoken_alias):
        return jsonify({'status': 'error', 'error': 'All alias fields are required'}), 400

    result = service.add_alias(entity_type, entity_id, resolved_name, spoken_alias)
    return jsonify(result)

@app.route('/api/aliases/<int:alias_id>', methods=['DELETE'])
def delete_alias_route(alias_id):
    from backend.app.intent_parser import DB_PATH
    from backend.app.services.alias_service import AliasService
    service = AliasService(DB_PATH)
    return jsonify(service.delete_alias(alias_id))

@app.route('/api/evaluation/benchmark', methods=['GET'])
def get_evaluation_benchmark():
    import json
    eval_dir = os.path.join(os.path.dirname(__file__), 'evaluation')
    results_path = os.path.join(eval_dir, 'benchmark_results.json')
    split = request.args.get('split') # e.g. 'held_out_test' or None for all

    if not os.path.exists(results_path):
        from backend.app.evaluation.benchmark_cli import run_all_benchmarks
        run_all_benchmarks(eval_dir)

    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if split == 'held_out_test' and "ProductionPipeline" in data and "HeldOutTest" in data["ProductionPipeline"]:
            split_data = data["ProductionPipeline"]["HeldOutTest"]
            return jsonify({
                'status': 'success',
                **split_data,
                'Metadata': data.get('Metadata', {}),
                'PipelineType': 'ProductionPipeline'
            })
        elif split == 'evaluation_set' and "ProductionPipeline" in data and "EvaluationSet" in data["ProductionPipeline"]:
            split_data = data["ProductionPipeline"]["EvaluationSet"]
            return jsonify({
                'status': 'success',
                **split_data,
                'Metadata': data.get('Metadata', {}),
                'PipelineType': 'ProductionPipeline'
            })
        return jsonify({'status': 'success', **data})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

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

@app.route('/api/commands/<command_id>/confirm', methods=['POST'])
def confirm_command_route(command_id):
    from backend.app.intent_parser import DB_PATH
    from backend.app.services.command_service import CommandService
    from backend.app.services.transaction_service import TransactionService

    service = CommandService(DB_PATH)
    cmd = service.get_command(command_id)
    if not cmd:
        return jsonify({'status': 'error', 'error': 'Command not found'}), 404

    op = cmd.get("Operation")
    if op == "sale":
        result = service.confirm_command(command_id, TransactionService.commit_sale)
    elif op == "restock":
        result = service.confirm_command(command_id, TransactionService.commit_restock)
    elif op == "credit":
        result = service.confirm_command(command_id, TransactionService.commit_credit)
    elif op == "udhaar_sale":
        result = service.confirm_command(command_id, TransactionService.commit_udhaar_sale)
    elif op == "repayment":
        result = service.confirm_command(command_id, TransactionService.commit_repayment)
    else:
        return jsonify({'status': 'error', 'error': f'Unsupported operation {op}'}), 400

    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/commands/<command_id>/cancel', methods=['POST'])
def cancel_command_route(command_id):
    from backend.app.intent_parser import DB_PATH
    from backend.app.services.command_service import CommandService

    service = CommandService(DB_PATH)
    result = service.cancel_command(command_id)
    status_code = 200 if result.get("status") == "success" else 400
    return jsonify(result), status_code

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    import tempfile
    if 'audio' not in request.files:
        return jsonify({'status': 'error', 'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    temp_audio_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_audio_path = temp_audio_file.name
    temp_audio_file.close()

    try:
        audio_file.save(temp_audio_path)
        
        preferred_lang = request.form.get('lang', 'hi-IN')
        
        # Get transcription via SDK (hi-IN handles Hindi and code-switched Hinglish natively)
        raw_transcript = transcribe_audio(temp_audio_path, language_code=preferred_lang)

        # If empty and preferred_lang was en-IN, try hi-IN (or vice-versa)
        if raw_transcript is not None and not raw_transcript.strip():
            fallback_lang = "en-IN" if preferred_lang == "hi-IN" else "hi-IN"
            fallback_transcript = transcribe_audio(temp_audio_path, language_code=fallback_lang)
            if fallback_transcript and fallback_transcript.strip():
                raw_transcript = fallback_transcript

        if raw_transcript is None:
            return jsonify({'status': 'error', 'error': 'Could not reach speech recognition service. Check your internet connection and API key.'}), 503

        if not raw_transcript.strip():
            return jsonify({'status': 'error', 'error': 'No speech detected. Please speak clearly into your microphone and click Send.'}), 400

        hindi_transcript = None
        if extract_explicit_quantity(raw_transcript) is None:
            hindi_transcript = transcribe_audio(temp_audio_path, language_code="hi-IN")

        from backend.app.intent_parser import DB_PATH
        from backend.app.services.query_service import QueryService
        try:
            store_kpis = QueryService(DB_PATH).get_store_kpis()
        except Exception:
            store_kpis = {}

        try:
            interpretation = understand_command(
                transcript=raw_transcript,
                hindi_transcript=hindi_transcript,
                inventory=get_db_records("Inventory", "ItemName"),
                customers=get_db_records("CustomerCredit", "CustomerName"),
                language_hint=preferred_lang,
                store_kpis=store_kpis,
            )
        except GeminiUnderstandingError as exc:
            return jsonify({
                "status": "error",
                "error": str(exc),
                "transcript": raw_transcript,
            }), 503

        # Execute only after the model's fields have been validated by the parser.
        db_result = parse_and_execute(raw_transcript, interpretation=interpretation)
        if isinstance(db_result, dict) and interpretation.get("spoken_response"):
            if db_result.get("action") == "assistant_qa" or not db_result.get("message"):
                db_result["message"] = interpretation["spoken_response"]

        return jsonify({
            'status': 'success',
            'transcript': raw_transcript,
            'database_action': db_result
        })
    finally:
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except Exception as e:
                print(f"Warning: Failed to clean up temp audio {temp_audio_path}: {e}")

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