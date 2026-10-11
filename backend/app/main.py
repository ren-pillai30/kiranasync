import os
import sys
import tempfile
import sqlite3
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from gnani.stt import GnaniSTTClient

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

sys.path.append(get_resource_path('backend/app'))
from intent_parser import parse_and_execute

load_dotenv(get_resource_path('.env'))

static_folder_path = get_resource_path('frontend/dist')
app = Flask(__name__, static_folder=static_folder_path, static_url_path='/')
gnani_client = GnaniSTTClient(api_key=os.getenv("GNANI_API_KEY"))

def query_db(query, args=(), one=False):
    db_path = get_resource_path('kirana.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/')
def serve_frontend():
    return app.send_static_file('index.html')

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        audio_file.save(temp_audio.name)
        temp_path = temp_audio.name

    try:
        result = gnani_client.transcribe(temp_path, language_code="hi-IN")
        if os.path.exists(temp_path): os.remove(temp_path)
        
        transcript = result.get("transcript", "")
        db_result = parse_and_execute(transcript)
        return jsonify({"status": "success", "transcript": transcript, "database_action": db_result})
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        return jsonify({"error": str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    try:
        inventory = [dict(row) for row in query_db('SELECT ItemID, ItemName, StockQuantity, Price FROM Inventory ORDER BY ItemID DESC')]
        credit = [dict(row) for row in query_db('SELECT CustomerID, CustomerName, OutstandingBalance FROM CustomerCredit ORDER BY CustomerID DESC')]
        return jsonify({"status": "success", "inventory": inventory, "credit": credit})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/inventory/add', methods=['POST'])
def add_inventory_ui():
    data = request.json
    try:
        db_path = get_resource_path('kirana.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute('INSERT INTO Inventory (ItemName, StockQuantity, Price) VALUES (?, ?, ?)', 
                    (data['ItemName'], int(data['StockQuantity']), float(data.get('Price', 0))))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/credit/add', methods=['POST'])
def add_credit_ui():
    data = request.json
    try:
        db_path = get_resource_path('kirana.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute('INSERT INTO CustomerCredit (CustomerName, OutstandingBalance) VALUES (?, ?)', 
                    (data['CustomerName'], float(data['Amount'])))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# NEW: Endpoints for editing spellings
@app.route('/api/inventory/edit', methods=['POST'])
def edit_inventory_ui():
    data = request.json
    try:
        db_path = get_resource_path('kirana.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute('UPDATE Inventory SET ItemName = ? WHERE ItemID = ?', 
                    (data['NewItemName'], data['ItemID']))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/credit/edit', methods=['POST'])
def edit_credit_ui():
    data = request.json
    try:
        db_path = get_resource_path('kirana.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute('UPDATE CustomerCredit SET CustomerName = ? WHERE CustomerID = ?', 
                    (data['NewCustomerName'], data['CustomerID']))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='127.0.0.1', port=port, debug=False)