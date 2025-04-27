// DOM elements
const startCameraBtn = document.getElementById('startCameraBtn');
const stopCameraBtn = document.getElementById('stopCameraBtn');
const toggleRecognitionBtn = document.getElementById('toggleRecognitionBtn');
const captureBtn = document.getElementById('captureBtn');
const uploadBtn = document.getElementById('uploadBtn');
const personNameInput = document.getElementById('personName');
const fileInput = document.getElementById('fileInput');
const videoFeed = document.getElementById('videoFeed');
const registeredFacesContainer = document.getElementById('registeredFaces');
const statusMessage = document.getElementById('statusMessage');
const loadingIndicator = document.getElementById('loadingIndicator');

// Camera state variables
let cameraActive = false;
let recognitionActive = false;

// Show status message function
function showStatus(message, isError = false) {
    statusMessage.textContent = message;
    statusMessage.className = isError ? 'error' : 'success';
    statusMessage.style.display = 'block';
    
    // Hide message after 3 seconds
    setTimeout(() => {
        statusMessage.style.display = 'none';
    }, 3000);
}

// Toggle loading indicator
function toggleLoading(show) {
    loadingIndicator.style.display = show ? 'block' : 'none';
}

// Update button states based on camera status
function updateButtonStates() {
    startCameraBtn.disabled = cameraActive;
    stopCameraBtn.disabled = !cameraActive;
    toggleRecognitionBtn.disabled = !cameraActive;
    captureBtn.disabled = !cameraActive || !personNameInput.value.trim();
    
    if (cameraActive) {
        startCameraBtn.classList.add('disabled');
        stopCameraBtn.classList.remove('disabled');
    } else {
        startCameraBtn.classList.remove('disabled');
        stopCameraBtn.classList.add('disabled');
    }
    
    if (recognitionActive) {
        toggleRecognitionBtn.textContent = 'Disable Recognition';
        toggleRecognitionBtn.classList.add('active');
    } else {
        toggleRecognitionBtn.textContent = 'Enable Recognition';
        toggleRecognitionBtn.classList.remove('active');
    }
}

// Load registered faces from the server
function loadRegisteredFaces() {
    toggleLoading(true);
    
    fetch('/get_registered_faces')
        .then(response => response.json())
        .then(data => {
            registeredFacesContainer.innerHTML = '';
            
            if (data.faces && data.faces.length > 0) {
                data.faces.forEach(face => {
                    const faceCard = document.createElement('div');
                    faceCard.className = 'face-card';
                    
                    const faceImg = document.createElement('img');
                    faceImg.src = face.image_path;
                    faceImg.alt = face.name;
                    faceImg.className = 'face-image';
                    
                    const faceName = document.createElement('div');
                    faceName.className = 'face-name';
                    faceName.textContent = face.name;
                    
                    const deleteBtn = document.createElement('button');
                    deleteBtn.className = 'delete-btn';
                    deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                    deleteBtn.onclick = () => deleteFace(face.name, face.filename);
                    
                    faceCard.appendChild(faceImg);
                    faceCard.appendChild(faceName);
                    faceCard.appendChild(deleteBtn);
                    
                    registeredFacesContainer.appendChild(faceCard);
                });
            } else {
                registeredFacesContainer.innerHTML = '<p class="no-faces">No registered faces yet.</p>';
            }
            
            toggleLoading(false);
        })
        .catch(error => {
            console.error('Error loading registered faces:', error);
            showStatus('Failed to load registered faces', true);
            toggleLoading(false);
        });
}

// Delete a registered face
function deleteFace(name, filename) {
    if (!confirm(`Are you sure you want to delete this face of ${name}?`)) {
        return;
    }
    
    toggleLoading(true);
    
    fetch('/delete_face', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, filename }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showStatus(data.message);
                loadRegisteredFaces();
            } else {
                showStatus(data.message, true);
            }
            toggleLoading(false);
        })
        .catch(error => {
            console.error('Error deleting face:', error);
            showStatus('Failed to delete face', true);
            toggleLoading(false);
        });
}

// Start camera
function startCamera() {
    toggleLoading(true);
    
    fetch('/start_camera', {
        method: 'POST',
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                cameraActive = true;
                videoFeed.src = '/video_feed?' + new Date().getTime();
                showStatus(data.message);
            } else {
                showStatus(data.message, true);
            }
            updateButtonStates();
            toggleLoading(false);
        })
        .catch(error => {
            console.error('Error starting camera:', error);
            showStatus('Failed to start camera', true);
            toggleLoading(false);
        });
}

// Stop camera
function stopCamera() {
    toggleLoading(true);
    
    fetch('/stop_camera', {
        method: 'POST',
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                cameraActive = false;
                recognitionActive = false;
                videoFeed.src = '';
                showStatus(data.message);
            } else {
                showStatus(data.message, true);
            }
            updateButtonStates();
            toggleLoading(false);
        })
        .catch(error => {
            console.error('Error stopping camera:', error);
            showStatus('Failed to stop camera', true);
            toggleLoading(false);
        });
}

// Toggle recognition
function toggleRecognition() {
    toggleLoading(true);
    
    fetch('/toggle_recognition', {
        method: 'POST',
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                recognitionActive = data.enabled;
                showStatus(data.message);
            } else {
                showStatus(data.message, true);
            }
            updateButtonStates();
            toggleLoading(false);
        })
        .catch(error => {
            console.error('Error toggling recognition:', error);
            showStatus('Failed to toggle recognition', true);
            toggleLoading(false);
        });
}

// Capture face
function captureFace() {
    const name = personNameInput.value.trim();
    
    if (!name) {
        showStatus('Please enter a name', true);
        return;
    }
    
    toggleLoading(true);
    
    fetch('/capture_face', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showStatus(data.message);
                loadRegisteredFaces();
                personNameInput.value = '';
            } else {
                showStatus(data.message, true);
            }
            toggleLoading(false);
        })
        .catch(error => {
            console.error('Error capturing face:', error);
            showStatus('Failed to capture face', true);
            toggleLoading(false);
        });
}

// Upload face
function uploadFace() {
    const name = personNameInput.value.trim();
    const file = fileInput.files[0];
    
    if (!name) {
        showStatus('Please enter a name', true);
        return;
    }
    
    if (!file) {
        showStatus('Please select a file', true);
        return;
    }
    
    toggleLoading(true);
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);
    
    fetch('/upload_face', {
        method: 'POST',
        body: formData,
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showStatus(data.message);
                loadRegisteredFaces();
                personNameInput.value = '';
                fileInput.value = '';
            } else {
                showStatus(data.message, true);
            }
            toggleLoading(false);
        })
        .catch(error => {
            console.error('Error uploading face:', error);
            showStatus('Failed to upload face', true);
            toggleLoading(false);
        });
}

// Update person name input validation
function updateCaptureButtonState() {
    captureBtn.disabled = !cameraActive || !personNameInput.value.trim();
    uploadBtn.disabled = !personNameInput.value.trim() || !fileInput.files.length;
}

// Event listeners
startCameraBtn.addEventListener('click', startCamera);
stopCameraBtn.addEventListener('click', stopCamera);
toggleRecognitionBtn.addEventListener('click', toggleRecognition);
captureBtn.addEventListener('click', captureFace);
uploadBtn.addEventListener('click', uploadFace);
personNameInput.addEventListener('input', updateCaptureButtonState);
fileInput.addEventListener('change', updateCaptureButtonState);

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    loadRegisteredFaces();
    updateButtonStates();
    updateCaptureButtonState();
    
    // Show welcome message
    showStatus('Welcome to Face Recognition App! Start the camera to begin.');
}); 