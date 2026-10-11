import os
import tempfile
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from gnani.stt import GnaniSTTClient

# Import the logic engine you just created
from intent_parser import parse_and_execute

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize the official Gnani STT Client
# This uses the GNANI_API_KEY from your .env file
gnani_client = GnaniSTTClient(api_key=os.getenv("GNANI_API_KEY"))

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check to verify server and API key status."""
    return jsonify({
        "status": "online",
        "gnani_configured": bool(os.getenv("GNANI_API_KEY"))
    })

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    """Receives audio from the frontend, gets transcript from Gnani, and updates DB."""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']
    
    # Save the file temporarily so the Gnani SDK can read it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        audio_file.save(temp_audio.name)
        temp_path = temp_audio.name

    try:
        # 1. Call the Gnani Vachana REST API
        # We use "hi-IN" for Hindi/Hinglish speech recognition
        result = gnani_client.transcribe(temp_path, language_code="hi-IN")
        
        # Clean up the temporary file immediately after transcription
        os.remove(temp_path)

        # 2. Extract the transcript
        transcript = result.get("transcript", "")
        
        # 3. Pass the transcript to the Intent Parser to modify the SQL Database
        db_result = parse_and_execute(transcript)
        
        # 4. Return the full result back to the frontend overlay
        return jsonify({
            "status": "success",
            "transcript": transcript,
            "database_action": db_result
        })
        
    except Exception as e:
        # Ensure the temp file is cleaned up even if Gnani API throws an error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)