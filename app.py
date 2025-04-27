import os
import cv2
import numpy as np
from flask import Flask, render_template, Response, jsonify, request, redirect, url_for
from deepface import DeepFace
import time
import threading
import datetime
import shutil
from werkzeug.utils import secure_filename
import base64
from PIL import Image
import io

app = Flask(__name__)

# Configuration
FACE_DATABASE = "face_database"
TEMP_DIR = "temp"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Create required directories if they don't exist
os.makedirs(FACE_DATABASE, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variables
camera = None
face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
face_recognition_enabled = False
lock = threading.Lock()
face_model = "VGG-Face"  # Can be "VGG-Face", "Facenet", "Facenet512", "OpenFace", "DeepFace", "DeepID", "ArcFace", "Dlib"
distance_metric = "cosine"  # Can be "cosine", "euclidean", "euclidean_l2"
face_detector_model = "opencv"  # Can be "opencv", "ssd", "dlib", "mtcnn", "retinaface", "mediapipe"
recognition_threshold = 0.4  # Lower is more strict

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def euclidean_distance(a, b):
    return np.sqrt(np.sum(np.square(a - b)))

def find_match(img_embedding, embeddings_dict, threshold=0.4):
    matches = []
    
    for name, embedding in embeddings_dict.items():
        # Calculate distance based on the selected metric
        if distance_metric == "cosine":
            distance = 1 - np.dot(img_embedding, embedding) / (np.linalg.norm(img_embedding) * np.linalg.norm(embedding))
        elif distance_metric == "euclidean":
            distance = euclidean_distance(img_embedding, embedding)
        elif distance_metric == "euclidean_l2":
            distance = euclidean_distance(img_embedding / np.linalg.norm(img_embedding), embedding / np.linalg.norm(embedding))
        
        # Consider it a match if distance is below threshold
        if distance < threshold:
            matches.append((name, distance))
    
    # Return the best match, if any
    if matches:
        return min(matches, key=lambda x: x[1])
    return None

def generate_frames():
    global face_recognition_enabled, face_detector
    
    while True:
        if camera is None:
            # Return a blank frame when the camera is not active
            blank_frame = np.zeros((480, 640, 3), np.uint8)
            cv2.putText(blank_frame, "Camera Off", (220, 240), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
            _, buffer = cv2.imencode('.jpg', blank_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)
            continue
        
        success, frame = camera.read()
        if not success:
            # Return a blank frame on camera read failure
            blank_frame = np.zeros((480, 640, 3), np.uint8)
            cv2.putText(blank_frame, "Camera Error", (220, 240), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
            _, buffer = cv2.imencode('.jpg', blank_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)
            continue
        
        # Flip the frame for a mirror effect
        frame = cv2.flip(frame, 1)
        
        # Convert frame to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces in the frame
        faces = face_detector.detectMultiScale(gray, 1.3, 5)
        
        # Process each detected face
        for (x, y, w, h) in faces:
            # Draw rectangle around face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # If face recognition is enabled, try to identify the face
            if face_recognition_enabled:
                try:
                    # Extract the face ROI
                    face_roi = frame[y:y+h, x:x+w].copy()
                    
                    # Only perform recognition if we have registered faces
                    if os.listdir(FACE_DATABASE):
                        # Analyze the face using DeepFace
                        result = DeepFace.find(
                            face_roi, 
                            db_path=FACE_DATABASE,
                            model_name=face_model,
                            distance_metric=distance_metric,
                            detector_backend=face_detector_model,
                            enforce_detection=False,
                            align=True
                        )
                        
                        # Check if any matches were found
                        if not result[0].empty:
                            # Get the best match
                            best_match = result[0].iloc[0]
                            distance = best_match[f"{distance_metric}_distance"]
                            
                            # Extract the name from the file path
                            path = best_match['identity']
                            name = os.path.basename(os.path.dirname(path))
                            
                            # Determine color based on confidence (green for high confidence, red for low)
                            if distance < recognition_threshold:
                                confidence = 1 - (distance / recognition_threshold)
                                color = (0, int(255 * confidence), int(255 * (1 - confidence)))
                                
                                # Display name and confidence on the frame
                                confidence_text = f"{confidence*100:.1f}%"
                                cv2.putText(frame, f"{name} ({confidence_text})", (x, y-10), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                            else:
                                # If distance is above threshold, show as unknown
                                cv2.putText(frame, "Unknown", (x, y-10), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                        else:
                            # No matches found in database
                            cv2.putText(frame, "Unknown", (x, y-10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                except Exception as e:
                    # Print exception for debugging
                    print(f"Error during face recognition: {e}")
                    # Display error message on frame
                    cv2.putText(frame, "Recognition Error", (x, y-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        
        # Convert the frame to JPEG format
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        # Yield the frame in the MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_camera', methods=['POST'])
def start_camera():
    global camera
    with lock:
        if camera is None:
            # Try to open the camera
            camera = cv2.VideoCapture(0)
            if not camera.isOpened():
                return jsonify({'status': 'error', 'message': 'Failed to open camera'}), 500
            # Set resolution to 640x480
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return jsonify({'status': 'success', 'message': 'Camera started'})

@app.route('/stop_camera', methods=['POST'])
def stop_camera():
    global camera
    with lock:
        if camera is not None:
            camera.release()
            camera = None
    return jsonify({'status': 'success', 'message': 'Camera stopped'})

@app.route('/toggle_recognition', methods=['POST'])
def toggle_recognition():
    global face_recognition_enabled
    face_recognition_enabled = not face_recognition_enabled
    return jsonify({
        'status': 'success', 
        'enabled': face_recognition_enabled,
        'message': f'Face recognition {"enabled" if face_recognition_enabled else "disabled"}'
    })

@app.route('/capture_face', methods=['POST'])
def capture_face():
    global camera
    
    # Check if camera is active
    if camera is None:
        return jsonify({'status': 'error', 'message': 'Camera is not active'}), 400
    
    # Get person name from form data
    data = request.get_json()
    person_name = data.get('name', '').strip()
    
    # Validate person name
    if not person_name:
        return jsonify({'status': 'error', 'message': 'Person name is required'}), 400
    
    # Create directory for this person if it doesn't exist
    person_dir = os.path.join(FACE_DATABASE, person_name)
    os.makedirs(person_dir, exist_ok=True)
    
    # Generate a timestamp for the filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Capture a frame from the camera
    ret, frame = camera.read()
    if not ret:
        return jsonify({'status': 'error', 'message': 'Failed to capture image'}), 500
    
    # Flip the frame for a mirror effect
    frame = cv2.flip(frame, 1)
    
    # Save the frame as an image file
    filename = f"{timestamp}.jpg"
    filepath = os.path.join(person_dir, filename)
    cv2.imwrite(filepath, frame)
    
    # Return success response with image path
    return jsonify({
        'status': 'success',
        'message': 'Face captured successfully',
        'image_path': f'/face_image/{person_name}/{filename}'
    })

@app.route('/upload_face', methods=['POST'])
def upload_face():
    # Check if name is provided
    person_name = request.form.get('name', '').strip()
    if not person_name:
        return jsonify({'status': 'error', 'message': 'Person name is required'}), 400
    
    # Check if file is provided
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    
    file = request.files['file']
    
    # Check if file is empty
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    
    # Check if file extension is allowed
    if not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'File type not allowed'}), 400
    
    # Create directory for this person if it doesn't exist
    person_dir = os.path.join(FACE_DATABASE, person_name)
    os.makedirs(person_dir, exist_ok=True)
    
    # Generate a timestamp for the filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{secure_filename(file.filename)}"
    filepath = os.path.join(person_dir, filename)
    
    # Save the uploaded file
    file.save(filepath)
    
    # Return success response with image path
    return jsonify({
        'status': 'success',
        'message': 'Face uploaded successfully',
        'image_path': f'/face_image/{person_name}/{filename}'
    })

@app.route('/face_image/<person_name>/<filename>')
def face_image(person_name, filename):
    return redirect(url_for('static', filename=f'../face_database/{person_name}/{filename}'))

@app.route('/get_registered_faces')
def get_registered_faces():
    faces = []
    
    # Check if the face database directory exists
    if not os.path.exists(FACE_DATABASE):
        return jsonify({'faces': faces})
    
    # Go through each person directory in the face database
    for person_name in os.listdir(FACE_DATABASE):
        person_dir = os.path.join(FACE_DATABASE, person_name)
        
        # Skip if not a directory
        if not os.path.isdir(person_dir):
            continue
        
        # Get all image files for this person
        for filename in os.listdir(person_dir):
            # Skip if not an image file
            if not allowed_file(filename):
                continue
            
            # Add to the list of faces
            faces.append({
                'name': person_name,
                'image_path': f'/face_image/{person_name}/{filename}',
                'filename': filename
            })
    
    return jsonify({'faces': faces})

@app.route('/delete_face', methods=['POST'])
def delete_face():
    data = request.get_json()
    person_name = data.get('name')
    filename = data.get('filename')
    
    if not person_name or not filename:
        return jsonify({'status': 'error', 'message': 'Name and filename are required'}), 400
    
    # Construct the file path
    filepath = os.path.join(FACE_DATABASE, person_name, filename)
    
    # Check if the file exists
    if not os.path.exists(filepath):
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    try:
        # Delete the file
        os.remove(filepath)
        
        # If this was the last image for the person, delete the person directory
        person_dir = os.path.join(FACE_DATABASE, person_name)
        if os.path.exists(person_dir) and not os.listdir(person_dir):
            os.rmdir(person_dir)
        
        return jsonify({'status': 'success', 'message': 'Face deleted successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error deleting file: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001) 