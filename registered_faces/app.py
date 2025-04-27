from flask import Flask, render_template, Response
import cv2
from deepface import DeepFace
import os

app = Flask(__name__)

db_path = "rcaptured_faces"
threshold = 0.4

video_capture = cv2.VideoCapture(0)

def generate_frames():
    while True:
        success, frame = video_capture.read()
        if not success:
            break
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            name = "Unknown"

            try:
                results = DeepFace.find(img_path=frame_rgb, db_path=db_path, enforce_detection=False)
                if len(results) > 0:
                    best_match = results[0]
                    best_identity = os.path.basename(best_match['identity'][0]).split('.')[0]
                    best_distance = best_match['VGG-Face_cosine'][0]

                    if best_distance <= threshold:
                        name = best_identity
                    else:
                        name = "Unknown"

            except Exception as e:
                name = "Unknown"

            # Draw name
            cv2.putText(frame, name, (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(debug=True)
