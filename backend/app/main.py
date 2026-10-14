import os
import sys
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from gnani.stt import GnaniSTTClient  # Official SDK client

# Explicitly load .env from the root directory
load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../.env'))
load_dotenv() # Fallback

from backend.app.intent_parser import parse_and_execute

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

template_dir = get_resource_path('frontend/dist')
static_dir = get_resource_path('frontend/dist/assets')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app)

def transcribe_audio(audio_path):
    """Calls Gnani Vachana STT API using the official SDK client."""
    api_key = os.getenv("GNANI_API_KEY")
    if not api_key:
        print("ERROR: GNANI_API_KEY is missing!")
        return None
    
    try:
        # Initialize the official SDK client
        client = GnaniSTTClient(api_key=api_key)
        
        # Transcribe audio using the official SDK method
        result = client.transcribe(audio_path, language_code="hi-IN")
        
        print(f"DEBUG: Gnani SDK Response -> {result}")
        
        if isinstance(result, dict):
            return result.get('transcript', '') or result.get('text', '')
        elif isinstance(result, str):
            return result
        else:
            return None
    except Exception as e:
        print(f"Gnani SDK Exception: {e}")
        return None

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

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({'status': 'error', 'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    temp_dir = '/tmp' if os.name != 'nt' else os.environ.get('TEMP', '.')
    audio_path = os.path.join(temp_dir, 'temp_command.wav')
    audio_file.save(audio_path)
    
    # Get transcription via SDK
    raw_transcript = transcribe_audio(audio_path)
    
    if not raw_transcript:
        return jsonify({'status': 'error', 'error': 'Failed to transcribe audio'}), 500

    # Execute intent
    db_result = parse_and_execute(raw_transcript)

    return jsonify({
        'status': 'success',
        'transcript': raw_transcript,
        'database_action': db_result
    })

@app.route('/api/inventory/add', methods=['POST'])
def add_inventory():
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)',
                   (data['ItemName'], data['StockQuantity'], data['Price']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/credit/add', methods=['POST'])
def add_credit():
    import sqlite3
    from backend.app.intent_parser import DB_PATH
    
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES (?, ?)',
                   (data['CustomerName'], data['Amount']))
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)',
                   (data['ItemName'], data['StockQuantity'], data['Price']))
    cursor.execute('INSERT INTO Transactions (CommandText, TotalAmount) VALUES (?, ?)', 
                   (data.get('RawCommand', 'Manual Confirmation'), 0))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)