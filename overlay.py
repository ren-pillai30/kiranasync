import os
from dotenv import load_dotenv

# Explicitly load .env and verify it
load_dotenv()
api_key_check = os.getenv("GNANI_API_KEY")

print("----------------------------------------")
print(f"DEBUG: Current Working Directory -> {os.getcwd()}")
print(f"DEBUG: .env File Exists -> {os.path.exists('.env')}")
if api_key_check:
    print(f"SUCCESS: GNANI_API_KEY loaded successfully! (Length: {len(api_key_check)}, Starts with: {api_key_check[:4]}...)")
else:
    print("CRITICAL ERROR: GNANI_API_KEY is STILL None or empty!")
print("----------------------------------------")

import sys
import threading
import webview
import keyboard
from backend.app.main import app  # Flask server

class DesktopAPI:
    def minimize(self):
        """Minimizes the pywebview desktop window."""
        if webview.windows:
            webview.windows[0].minimize()

    def close(self):
        """Closes the desktop application."""
        if webview.windows:
            webview.windows[0].destroy()

def run_flask():
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def bind_hotkeys(window):
    """Listens for global hotkeys and clicks the hidden React trigger buttons."""
    keyboard.add_hotkey('ctrl+shift+v', lambda: window.evaluate_js('document.getElementById("voice-trigger") && document.getElementById("voice-trigger").click()'))
    keyboard.add_hotkey('ctrl+shift+d', lambda: window.evaluate_js('document.getElementById("dashboard-trigger") && document.getElementById("dashboard-trigger").click()'))

if __name__ == '__main__':
    # Start Flask API in background thread
    server_thread = threading.Thread(target=run_flask, daemon=True)
    server_thread.start()

    api = DesktopAPI()
    
    # Launch Frameless pywebview HUD Overlay
    window = webview.create_window(
        title='KiranaSync Voice',
        url='http://127.0.0.1:5000',
        js_api=api,
        width=1000,
        height=700,
        frameless=True,
        on_top=True
    )
    
    # Start the webview and attach the hotkey listener
    webview.start(bind_hotkeys, window)