#!/usr/bin/env python3
"""
Simplified Face Recognition App
Displays detected faces with names in red, bold text
"""

import os
import cv2
import time
import numpy as np
from flask import Flask, render_template, Response, jsonify, request
import threading

# Create face database directory if it doesn't exist
face_database_dir = 'face_database'
if not os.path.exists(face_database_dir):
    os.makedirs(face_database_dir)

app = Flask(__name__)

# Global variables
camera = None
camera_active = False
recognize_faces = True  # Set to True by default to immediately recognize faces
lock = threading.Lock()
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def find_matching_face(face_img, threshold=0.6):
    """Find matching face in the database using template matching"""
    best_match = None
    best_match_score = 0
    
    # Resize face image for comparison
    face_img_small = cv2.resize(face_img, (100, 100))
    
    # Loop through all faces in the database
    if os.path.exists(face_database_dir):
        for filename in os.listdir(face_database_dir):
            if not filename.endswith(('.jpg', '.jpeg', '.png')):
                continue
                
            try:
                # Load the database face
                db_face_path = os.path.join(face_database_dir, filename)
                db_face = cv2.imread(db_face_path)
                if db_face is None:
                    continue
                
                # Resize database face to the same size
                db_face_small = cv2.resize(db_face, (100, 100))
                
                # Convert both faces to grayscale
                face_gray = cv2.cvtColor(face_img_small, cv2.COLOR_BGR2GRAY)
                db_face_gray = cv2.cvtColor(db_face_small, cv2.COLOR_BGR2GRAY)
                
                # Compare using template matching
                result = cv2.matchTemplate(db_face_gray, face_gray, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                # If this match is better than our previous best, update
                if max_val > best_match_score and max_val > threshold:
                    best_match_score = max_val
                    best_match = os.path.splitext(filename)[0]  # Get name without extension
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                continue
                
    return best_match, best_match_score

def generate_frames():
    """Generate frames from the camera with face detection and recognition"""
    global camera, camera_active, recognize_faces
    
    while True:
        with lock:
            if not camera_active or camera is None:
                # Return an empty frame if camera is not active
                empty_frame = np.zeros((480, 640, 3), np.uint8)
                cv2.putText(empty_frame, "Camera Off", (220, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                _, buffer = cv2.imencode('.jpg', empty_frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.1)  # Prevent excessive CPU usage
                continue
            
            success, frame = camera.read()
            if not success:
                empty_frame = np.zeros((480, 640, 3), np.uint8)
                cv2.putText(empty_frame, "Camera Error", (220, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                _, buffer = cv2.imencode('.jpg', empty_frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                continue
                
            # Mirror the frame horizontally (selfie mode)
            frame = cv2.flip(frame, 1)
            
            # Detect faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # Process each detected face
            for (x, y, w, h) in faces:
                # Draw rectangle around the face - make it thicker (3 pixels)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 3)
                
                # Extract the face region
                face_img = frame[y:y+h, x:x+w]
                
                # Find matching face
                match_name, confidence = find_matching_face(face_img)

                print(f"Match: {match_name}, Confidence: {confidence:.2f}")
                
                if match_name:
                    # Display the name in RED and BOLD (larger font size and thickness)
                    label = f"{match_name} ({confidence:.2f})"
                    
                    # Add a dark background for better visibility of the red text
                    text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 1.2, 3)[0]
                    cv2.rectangle(frame, 
                                 (x, y - text_size[1] - 10), 
                                 (x + text_size[0] + 10, y), 
                                 (0, 0, 0), -1)
                    
                    # Draw the name text in red, bold
                    cv2.putText(frame, label, 
                               (x + 5, y - 5), 
                               cv2.FONT_HERSHEY_DUPLEX, 
                               1.2,  # Larger font 
                               (0, 0, 255),  # RED color
                               3)  # Thicker text
                else:
                    captured_once = False

                    # Display "Unknown" in red
                    # Add a dark background for better visibility
                    text_size = cv2.getTextSize("Unknown", cv2.FONT_HERSHEY_DUPLEX, 1.2, 3)[0]
                    cv2.rectangle(frame, 
                                 (x, y - text_size[1] - 10), 
                                 (x + text_size[0] + 10, y), 
                                 (0, 0, 0), -1)
                    
                    # Draw "Unknown" text in red, bold
                    cv2.putText(frame, "Unknown", 
                               (x + 5, y - 5), 
                               cv2.FONT_HERSHEY_DUPLEX, 
                               1.2,  # Larger font
                               (0, 0, 255),  # RED color
                               3)  # Thicker text
                    
                    if not captured_once:
                        captured_face = cv2.resize(face_img, (100, 100))
                        # Save the unknown face to the database
                        unknown_face_path = os.path.join(face_database_dir, f"unknown{int(time.time())}.jpg")
                        cv2.imwrite(unknown_face_path, captured_face)
                        print(f"Unknown face saved to {unknown_face_path}")
                        captured_once = True
                                
            # Add recognition status overlay
            status_text = "Recognition: ON"
            cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Convert to jpg and yield
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# Routes
@app.route('/')
def index():
    """Serve a simple HTML page with video feed"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Face Recognition</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }
            .container { max-width: 800px; margin: 0 auto; }
            .video-container { margin-bottom: 20px; }
            .controls { margin-bottom: 20px; }
            .btn { padding: 10px 20px; margin: 5px; cursor: pointer; }
            img { max-width: 100%; border: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Face Recognition App</h1>
            <div class="video-container">
                <img src="/video_feed" alt="Video Feed">
            </div>
            <div class="controls">
                <button class="btn" onclick="fetch('/start_camera', {method: 'POST'})">Start Camera</button>
                <button class="btn" onclick="fetch('/stop_camera', {method: 'POST'})">Stop Camera</button>
                <a href="http://localhost:8000/label_unknown_faces"><button class="btn">Label Faces</button></a>
            </div>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/label_unknown_faces', methods=['POST', 'GET'])
def label_unknown_faces():
    if request.method == 'GET':
        # Return the list of unknown faces
        unknown_faces = ["http://localhost:8000/static/" + str(f) for f in os.listdir(face_database_dir) if f.startswith('unknown')]
        return jsonify({"unknown_faces": unknown_faces})
    
    return jsonify({"success": False, "message": "Invalid request method"})


@app.route("/static/<filename>", methods=["GET"])
def static_file(filename):
    """Serve static files"""
    try:
        file_path = os.path.join("face_database", filename)
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        # Open the file in binary mode
        with open(file_path, "rb") as f:
            return Response(f.read(), mimetype="image/jpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stop_camera', methods=['POST'])
def stop_camera():
    """Stop the camera"""
    global camera, camera_active
    try:
        with lock:
            camera_active = False
            if camera is not None:
                camera.release()
                camera = None
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/static/<filename>", methods=["GET"])
def static_files(filename):
    """Serve static files"""
    with open(f"face_database/{filename}", "r") as f:
        return Response(f.read(), mimetype="image/jpeg")

if __name__ == '__main__':
    print("Face Recognition App starting...")
    print("Access the app at http://localhost:8000")
    app.run(host='0.0.0.0', port=8000, debug=True, threaded=True) 