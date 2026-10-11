import webview
import keyboard
import threading
import time
import sys
import os

# Helper function to handle resource paths when bundled with PyInstaller
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Ensure backend module can be imported
sys.path.append(get_resource_path('backend/app'))
from main import app

def start_server():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def trigger_voice_copilot(window):
    print("Voice Hotkey pressed!")
    window.evaluate_js("document.getElementById('voice-trigger').click()")

def trigger_dashboard(window):
    print("Dashboard Hotkey pressed!")
    window.evaluate_js("document.getElementById('dashboard-trigger').click()")

if __name__ == '__main__':
    # 1. Start Flask API background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    time.sleep(2)

    # 2. Create the transparent, borderless window
    window = webview.create_window(
        'KiranaSync Copilot',
        'http://127.0.0.1:5000',
        transparent=True,
        frameless=True,
        on_top=True,
        width=1000,
        height=800,
        x=450,
        y=150
    )

    # 3. Bind global hotkeys
    keyboard.add_hotkey('ctrl+shift+space', trigger_voice_copilot, args=[window])
    keyboard.add_hotkey('ctrl+shift+d', trigger_dashboard, args=[window])

    print("Daemon running.")
    print(" - Press Ctrl+Shift+Space to speak.")
    print(" - Press Ctrl+Shift+D to toggle live dashboard.")
    
    webview.start()