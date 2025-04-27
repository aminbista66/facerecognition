import os
import webbrowser
import time
import threading

# Create face database directory if it doesn't exist
FACE_DATABASE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'face_database')
TEMP_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'temp')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'uploads')

# Ensure directories exist
os.makedirs(FACE_DATABASE, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Start Flask app in a separate thread
def start_app():
    os.system('python app.py')

# Open the browser
def open_browser():
    time.sleep(2)  # Wait for the server to start
    webbrowser.open('http://localhost:5001')

if __name__ == '__main__':
    # Start the Flask app in a separate thread
    app_thread = threading.Thread(target=start_app)
    app_thread.daemon = True
    app_thread.start()
    
    # Open the browser
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...") 