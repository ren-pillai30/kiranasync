import os
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
        width=1000,   # Increased width to fit the dashboard
        height=700,   # Increased height to fit the dashboard
        frameless=True,
        on_top=True
    )
    
    # Start the webview and attach the hotkey listener
    webview.start(bind_hotkeys, window)