import os
from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "gnani_configured": bool(os.getenv("GNANI_API_KEY"))
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)