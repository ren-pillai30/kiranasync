import os
import sys
import math

if __package__ in (None, ""):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
from dotenv import load_dotenv
import requests
from flask_login import current_user

# Explicitly load .env from the root directory
load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../.env'))
load_dotenv() # Fallback

from backend.app.database import db, get_database_url
from backend.app.auth import login_manager, register_auth_routes

app_config_database_url = get_database_url()

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

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir, static_url_path='/assets')
CORS(app, supports_credentials=True)

app.config["SQLALCHEMY_DATABASE_URI"] = app_config_database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SESSION_SECRET", os.urandom(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.getenv("KIRANA_ENV") == "production"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.init_app(app)
login_manager.init_app(app)
register_auth_routes(app)

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return error
    app.logger.exception("Unhandled application error: %s", error)
    if request.path.startswith("/api/"):
        return jsonify({
            "status": "error",
            "error": "The server encountered an error while processing the request.",
        }), 500
    if app.testing:
        raise error
    return render_template("index.html"), 500

from backend.app import models  # noqa: F401,E402

with app.app_context():
    db.create_all()

@app.before_request
def require_authenticated_session():
    if app.testing or app.config.get("TESTING") or app.config.get("LOGIN_DISABLED"):
        return None
    if os.getenv("KIRANA_AUTH_ENABLED", "true").lower() in ("false", "0", "no"):
        return None
    if not request.path.startswith("/api/"):
        return None
    if request.path.startswith("/api/auth/"):
        return None
    if request.path.startswith("/api/") and not current_user.is_authenticated:
        return jsonify({"status": "error", "error": "Authentication required."}), 401

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
    from backend.app.gemini_understanding import (
        GeminiUnderstandingError,
        translate_for_speech,
    )
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    language_code = data.get("language_code", "hi-IN")

    if not text:
        return jsonify({'status': 'error', 'error': 'Text is required'}), 400

    try:
        text = translate_for_speech(text, language_code)
        audio_bytes, content_type = tts_provider.synthesize(text, language_code=language_code)
        return Response(audio_bytes, mimetype=content_type)
    except GeminiUnderstandingError as e:
        return jsonify({'status': 'error', 'error': str(e)}), 503
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 503

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(template_dir, 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    response = send_from_directory(template_dir, 'sw.js')
    response.headers['Service-Worker-Allowed'] = '/'
    return response

@app.route('/favicon.svg')
def serve_favicon():
    return send_from_directory(template_dir, 'favicon.svg')

@app.route('/icons.svg')
def serve_icons():
    return send_from_directory(template_dir, 'icons.svg')

@app.route('/<path:path>')
def serve_spa_fallback(path):
    if path.startswith("api/"):
        return jsonify({"status": "error", "error": "API endpoint not found."}), 404
    file_path = os.path.join(template_dir, path)
    if os.path.isfile(file_path):
        return send_from_directory(template_dir, path)
    return render_template('index.html')

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    ensure_transactions_schema(conn)
    cursor = conn.cursor()
    
    cursor.execute('SELECT ItemID, ItemName, StockQuantity, Price FROM Inventory WHERE IsActive = 1')
    inventory = [{'ItemID': row[0], 'ItemName': row[1], 'StockQuantity': row[2], 'Price': row[3]} for row in cursor.fetchall()]
    
    cursor.execute('SELECT CustomerID, CustomerName, OutstandingBalance FROM CustomerCredit WHERE IsActive = 1')
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

@app.route('/api/archives', methods=['GET'])
def get_entity_archives():
    from backend.app.intent_parser import DB_PATH
    from backend.app.services.entity_service import EntityService

    return jsonify({
        'status': 'success',
        'archives': EntityService(DB_PATH).list_archives(),
    })

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
            'SELECT ItemName, StockQuantity, Price FROM Inventory WHERE ItemID = ? AND IsActive = 1',
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

@app.route('/api/transactions/confirm', methods=['POST'])
def confirm_transaction():
    import sqlite3
    from backend.app.intent_parser import DB_PATH

    data = request.get_json(silent=True) or {}
    intent = data.get('Intent')
    raw_command = str(data.get('RawCommand') or '').strip()

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_transactions_schema(conn)
        cursor = conn.cursor()

        if intent == 'credit':
            customer_name = str(data.get('CustomerName') or '').strip()
            try:
                amount = float(data.get('Amount'))
            except (TypeError, ValueError):
                amount = 0
            if not customer_name or amount <= 0:
                return jsonify({'status': 'error', 'error': 'A customer and positive amount are required.'}), 400

            cursor.execute(
                "SELECT CustomerID, OutstandingBalance FROM CustomerCredit WHERE lower(CustomerName) = lower(?)",
                (customer_name,),
            )
            customer = cursor.fetchone()
            if customer:
                new_balance = float(customer[1] or 0) + amount
                cursor.execute(
                    'UPDATE CustomerCredit SET OutstandingBalance = ?, IsActive = 1 WHERE CustomerID = ?',
                    (new_balance, customer[0]),
                )
                message = f"Added Rs {amount:g} to {customer_name}. New Balance: Rs {new_balance:g}."
            else:
                cursor.execute(
                    'INSERT INTO CustomerCredit (CustomerName, OutstandingBalance, IsActive) VALUES (?, ?, 1)',
                    (customer_name, amount),
                )
                new_balance = amount
                message = f"Created {customer_name}'s account with Rs {amount:g} balance."
            record_transaction(cursor, raw_command, amount, 'Credit', customer_name)
        else:
            return jsonify({'status': 'error', 'error': 'Unsupported transaction confirmation.'}), 400

        conn.commit()
        return jsonify({
            'status': 'success',
            'database_action': {'status': 'success', 'action': 'udhaar_added', 'message': message},
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

    missing_voice_config = []
    if not os.getenv('GNANI_API_KEY'):
        missing_voice_config.append('GNANI_API_KEY')
    if not (os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')):
        missing_voice_config.append('GEMINI_API_KEY or GOOGLE_API_KEY')
    if missing_voice_config:
        missing_names = ', '.join(missing_voice_config)
        return jsonify({
            'status': 'error',
            'error': f'Voice service configuration is missing on the server: {missing_names}.',
        }), 503
    
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

        if not raw_transcript or not raw_transcript.strip():
            return jsonify({
                'status': 'error',
                'error': (
                    'Speech recognition did not return a transcript. '
                    f'{stt_provider.last_error or "Speak clearly and try again."}'
                ),
            }), 502

        if raw_transcript is None:
            provider_error = stt_provider.last_error or 'Provider returned no transcript.'
            return jsonify({
                'status': 'error',
                'error': f'Speech recognition failed: {provider_error}',
            }), 503

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
    except Exception as exc:
        app.logger.exception("Voice command processing failed: %s", exc)
        return jsonify({
            'status': 'error',
            'error': f'Voice processing failed on the server: {str(exc)[:300]}',
        }), 500
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
    
    data = request.get_json(silent=True) or {}
    conn = sqlite3.connect(DB_PATH)
    ensure_transactions_schema(conn)
    cursor = conn.cursor()
    item_name = str(data.get('ItemName', '')).strip()
    try:
        quantity = int(data.get('StockQuantity'))
        price = float(data.get('Price'))
    except (TypeError, ValueError):
        conn.close()
        return jsonify({'status': 'error', 'error': 'Enter a valid whole-number stock quantity and price.'}), 400
    if not item_name or quantity < 0 or not math.isfinite(price) or price < 0:
        conn.close()
        return jsonify({'status': 'error', 'error': 'Enter a product name, non-negative stock, and valid price.'}), 400
    cursor.execute(
        'SELECT ItemID, IsActive FROM Inventory WHERE lower(ItemName) = lower(?)',
        (item_name,),
    )
    existing = cursor.fetchone()
    if existing and existing[1]:
        conn.close()
        return jsonify({'status': 'error', 'error': 'That product is already active in inventory.'}), 409
    if existing:
        cursor.execute(
            'UPDATE Inventory SET ItemName = ?, StockQuantity = ?, Price = ?, IsActive = 1 WHERE ItemID = ?',
            (item_name, quantity, price, existing[0]),
        )
    else:
        cursor.execute(
            'INSERT INTO Inventory (ItemName, StockQuantity, Price, IsActive) VALUES (?, ?, ?, 1)',
            (item_name, quantity, price),
        )
    record_transaction(
        cursor,
        f"Added {quantity} {item_name} to inventory",
        -price * quantity,
        "Restock",
        item_name,
        quantity,
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/credit/add', methods=['POST'])
def add_credit():
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    data = request.get_json(silent=True) or {}
    conn = sqlite3.connect(DB_PATH)
    ensure_transactions_schema(conn)
    cursor = conn.cursor()
    customer_name = str(data.get('CustomerName', '')).strip()
    try:
        amount = float(data.get('Amount'))
    except (TypeError, ValueError):
        conn.close()
        return jsonify({'status': 'error', 'error': 'Enter a valid starting balance.'}), 400
    if not customer_name or not math.isfinite(amount) or amount < 0:
        conn.close()
        return jsonify({'status': 'error', 'error': 'Enter a customer name and non-negative balance.'}), 400
    cursor.execute(
        'SELECT CustomerID, OutstandingBalance, IsActive FROM CustomerCredit WHERE lower(CustomerName) = lower(?)',
        (customer_name,),
    )
    existing = cursor.fetchone()
    if existing and existing[2]:
        conn.close()
        return jsonify({'status': 'error', 'error': 'That customer is already active.'}), 409
    if existing:
        cursor.execute(
            'UPDATE CustomerCredit SET IsActive = 1, OutstandingBalance = ? WHERE CustomerID = ?',
            (float(existing[1] or 0) + amount, existing[0]),
        )
    else:
        cursor.execute(
            'INSERT INTO CustomerCredit (CustomerName, OutstandingBalance, IsActive) VALUES (?, ?, 1)',
            (customer_name, amount),
        )
    if amount > 0:
        record_transaction(
            cursor,
            f"Added starting credit for {customer_name}",
            amount,
            "Credit",
            customer_name,
        )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/entities/archive', methods=['POST'])
def archive_entity():
    from backend.app.intent_parser import DB_PATH
    from backend.app.services.entity_service import EntityService

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'error': 'Confirm a valid product or customer removal.'}), 400
    entity_type = data.get('EntityType')
    try:
        entity_id = int(data.get('EntityID'))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'error': 'Choose a valid product or customer.'}), 400
    if entity_type not in {'Product', 'Customer'} or entity_id <= 0:
        return jsonify({'status': 'error', 'error': 'Choose a valid product or customer.'}), 400

    service = EntityService(DB_PATH)
    if entity_type == 'Product':
        result = service.archive_inventory_item(
            entity_id,
            reason=data.get('Reason'),
            raw_command=data.get('RawCommand'),
        )
    else:
        result = service.archive_customer(
            entity_id,
            reason=data.get('Reason'),
            raw_command=data.get('RawCommand'),
        )
    status_code = 200 if result.get('status') == 'success' else 404
    return jsonify(result), status_code

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
                'SELECT ItemID, IsActive FROM Inventory WHERE lower(ItemName) = lower(?)',
                (variant_name,),
            )
            existing = cursor.fetchone()
            if existing and existing[1]:
                raise sqlite3.IntegrityError("An active product variant already exists.")
            if existing:
                cursor.execute(
                    'UPDATE Inventory SET StockQuantity = ?, Price = ?, IsActive = 1 WHERE ItemID = ?',
                    (quantity, price, existing[0]),
                )
            else:
                cursor.execute(
                    'INSERT INTO Inventory (ItemName, StockQuantity, Price, IsActive) VALUES (?, ?, ?, 1)',
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
    added_names = ", ".join(
        f"{item_name.strip()} (MRP ₹{item['Price']:g})"
        for item in items
    )
    return jsonify({
        'status': 'success',
        'database_action': {
            'status': 'success',
            'action': 'product_added',
            'message': f"Added {added_names} to inventory.",
        },
    })


def ensure_feedback_schema(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS StoreFeedback (
            FeedbackID INTEGER PRIMARY KEY AUTOINCREMENT,
            Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            Rating INTEGER,
            Category TEXT,
            Message TEXT,
            Author TEXT
        )
        """
    )
    connection.commit()

@app.route('/api/feedback', methods=['GET', 'POST'])
def handle_store_feedback():
    import sqlite3
    from backend.app.intent_parser import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    ensure_feedback_schema(conn)

    if request.method == 'GET':
        cursor = conn.cursor()
        cursor.execute(
            "SELECT FeedbackID, Timestamp, Rating, Category, Message, Author FROM StoreFeedback ORDER BY FeedbackID DESC LIMIT 50"
        )
        rows = [
            {
                "FeedbackID": r[0],
                "Timestamp": r[1],
                "Rating": r[2],
                "Category": r[3],
                "Message": r[4],
                "Author": r[5] or "Store Cashier",
            }
            for r in cursor.fetchall()
        ]
        conn.close()
        return jsonify({"status": "success", "feedback": rows})

    data = request.get_json(silent=True) or {}
    message = str(data.get("message") or "").strip()
    if not message:
        conn.close()
        return jsonify({"status": "error", "error": "Feedback message cannot be empty."}), 400

    try:
        rating = int(data.get("rating", 5))
        rating = max(1, min(5, rating))
    except (ValueError, TypeError):
        rating = 5

    category = str(data.get("category") or "General").strip()
    author = str(data.get("author") or "Store Cashier").strip()

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO StoreFeedback (Rating, Category, Message, Author) VALUES (?, ?, ?, ?)",
        (rating, category, message, author),
    )
    conn.commit()
    conn.close()
    return jsonify({
        "status": "success",
        "message": "Thank you! Your feedback has been recorded.",
    })


@app.route('/api/barcode/lookup', methods=['GET', 'POST'])
def barcode_lookup():
    """Look up an inventory item by barcode or alias code."""
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    code = request.args.get('code')
    if not code and request.is_json:
        code = request.get_json(silent=True).get('code')
    code = str(code or '').strip()
    if not code:
        return jsonify({'status': 'error', 'error': 'Barcode number is required.'}), 400

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_transactions_schema(conn)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(Inventory)")
        inv_cols = {col[1] for col in cursor.fetchall()}
        if "Barcode" in inv_cols:
            cursor.execute(
                "SELECT ItemID, ItemName, StockQuantity, Price FROM Inventory WHERE Barcode = ? AND IsActive = 1",
                (code,)
            )
            row = cursor.fetchone()
            if row:
                return jsonify({
                    'status': 'success',
                    'found': True,
                    'item': {
                        'ItemID': row[0],
                        'ItemName': row[1],
                        'StockQuantity': row[2],
                        'Price': float(row[3]),
                    }
                })

        cursor.execute(
            "SELECT EntityID, ResolvedName FROM Aliases WHERE SpokenAlias = ? AND EntityType = 'Product' AND IsApproved = 1",
            (code,)
        )
        alias_row = cursor.fetchone()
        if alias_row:
            cursor.execute(
                "SELECT ItemID, ItemName, StockQuantity, Price FROM Inventory WHERE ItemID = ? AND IsActive = 1",
                (alias_row[0],)
            )
            item_row = cursor.fetchone()
            if item_row:
                return jsonify({
                    'status': 'success',
                    'found': True,
                    'item': {
                        'ItemID': item_row[0],
                        'ItemName': item_row[1],
                        'StockQuantity': item_row[2],
                        'Price': float(item_row[3]),
                    }
                })

        cursor.execute(
            "SELECT ItemID, ItemName, StockQuantity, Price FROM Inventory WHERE (ItemName LIKE ? OR ItemName LIKE ?) AND IsActive = 1",
            (f"%{code}%", f"%({code})%")
        )
        fuzzy_row = cursor.fetchone()
        if fuzzy_row:
            return jsonify({
                'status': 'success',
                'found': True,
                'item': {
                    'ItemID': fuzzy_row[0],
                    'ItemName': fuzzy_row[1],
                    'StockQuantity': fuzzy_row[2],
                    'Price': float(fuzzy_row[3]),
                }
            })

        return jsonify({'status': 'success', 'found': False, 'message': f'No product found for barcode {code}.'})
    finally:
        conn.close()

@app.route('/api/barcode/link', methods=['POST'])
def barcode_link():
    """Link a barcode to an existing inventory item."""
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    data = request.get_json(silent=True) or {}
    item_id = data.get('ItemID')
    barcode = str(data.get('Barcode') or '').strip()
    if not item_id or not barcode:
        return jsonify({'status': 'error', 'error': 'ItemID and Barcode are required.'}), 400

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_transactions_schema(conn)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Inventory)")
        inv_cols = {col[1] for col in cursor.fetchall()}
        if "Barcode" not in inv_cols:
            cursor.execute("ALTER TABLE Inventory ADD COLUMN Barcode TEXT")
        
        cursor.execute(
            "UPDATE Inventory SET Barcode = ? WHERE ItemID = ?",
            (barcode, item_id)
        )
        cursor.execute("SELECT ItemName FROM Inventory WHERE ItemID = ?", (item_id,))
        item = cursor.fetchone()
        if item:
            cursor.execute(
                "INSERT OR REPLACE INTO Aliases (EntityType, EntityID, ResolvedName, SpokenAlias, IsApproved) VALUES ('Product', ?, ?, ?, 1)",
                (item_id, item[0], barcode)
            )
        conn.commit()
        return jsonify({'status': 'success', 'message': f'Barcode {barcode} linked successfully.'})
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=os.getenv('FLASK_DEBUG') == '1')