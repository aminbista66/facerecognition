document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const videoFeed = document.getElementById('video-feed');
    const cameraPlaceholder = document.getElementById('camera-placeholder');
    const cameraToggle = document.getElementById('camera-toggle');
    const captureBtn = document.getElementById('capture-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadInput = document.getElementById('upload-input');
    const faceName = document.getElementById('face-name');
    const refreshFaces = document.getElementById('refresh-faces');
    const resetDb = document.getElementById('reset-db');
    const facesContainer = document.getElementById('faces-container');
    const faceCountDisplay = document.querySelectorAll('.face-count-display');
    const faceCount = document.getElementById('face-count');
    const cameraStatus = document.getElementById('camera-status');
    const recognitionStatus = document.getElementById('recognition-status');
    
    // Capture modal elements
    const captureModal = new bootstrap.Modal(document.getElementById('capture-modal'));
    const capturedImage = document.getElementById('captured-image');
    const capturedName = document.getElementById('captured-name');
    const registerBtn = document.getElementById('register-btn');
    
    // Preview modal elements
    const previewModal = new bootstrap.Modal(document.getElementById('preview-modal'));
    const previewImage = document.getElementById('preview-image');
    const uploadName = document.getElementById('upload-name');
    const confirmUploadBtn = document.getElementById('confirm-upload-btn');
    
    // Canvas for image processing
    const processCanvas = document.getElementById('process-canvas');
    const ctx = processCanvas.getContext('2d');
    
    // App state
    let cameraRunning = false;
    let recognitionRunning = true;
    
    // Initialize
    loadRegisteredFaces();
    
    // Event listeners
    cameraToggle.addEventListener('click', toggleCamera);
    captureBtn.addEventListener('click', captureFace);
    uploadBtn.addEventListener('click', () => uploadInput.click());
    uploadInput.addEventListener('change', previewUpload);
    registerBtn.addEventListener('click', registerCapturedFace);
    confirmUploadBtn.addEventListener('click', registerUploadedFace);
    refreshFaces.addEventListener('click', loadRegisteredFaces);
    resetDb.addEventListener('click', confirmResetDatabase);
    
    // Camera control functions
    function toggleCamera() {
        if (cameraRunning) {
            stopCamera();
        } else {
            startCamera();
        }
    }
    
    function startCamera() {
        fetch('/start_camera')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    cameraRunning = true;
                    videoFeed.style.display = 'block';
                    cameraPlaceholder.style.display = 'none';
                    captureBtn.disabled = false;
                    cameraToggle.innerHTML = '<i class="bi bi-camera-video-off"></i> Stop Camera';
                    cameraToggle.classList.replace('btn-primary', 'btn-danger');
                    cameraStatus.innerHTML = '<span class="status-indicator status-on me-2"></span> Camera: On';
                    cameraStatus.classList.replace('bg-secondary', 'bg-primary');
                    
                    // Start loading frames
                    videoFeed.src = '/video_feed?' + new Date().getTime();
                }
            })
            .catch(error => console.error('Error starting camera:', error));
    }
    
    function stopCamera() {
        fetch('/stop_camera')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    cameraRunning = false;
                    videoFeed.style.display = 'none';
                    cameraPlaceholder.style.display = 'flex';
                    captureBtn.disabled = true;
                    cameraToggle.innerHTML = '<i class="bi bi-camera-video"></i> Start Camera';
                    cameraToggle.classList.replace('btn-danger', 'btn-primary');
                    cameraStatus.innerHTML = '<span class="status-indicator me-2"></span> Camera: Off';
                    cameraStatus.classList.replace('bg-primary', 'bg-secondary');
                    
                    // Stop loading frames
                    videoFeed.src = '';
                }
            })
            .catch(error => console.error('Error stopping camera:', error));
    }
    
    // Face capture and registration
    function captureFace() {
        if (!cameraRunning) return;
        
        fetch('/capture_face')
            .then(response => response.blob())
            .then(blob => {
                capturedImage.src = URL.createObjectURL(blob);
                capturedName.value = faceName.value || '';
                captureModal.show();
            })
            .catch(error => console.error('Error capturing face:', error));
    }
    
    function registerCapturedFace() {
        const name = capturedName.value.trim();
        if (!name) {
            alert('Please enter a name for this face');
            return;
        }
        
        // Get the image data from the captured image
        processCanvas.width = capturedImage.naturalWidth;
        processCanvas.height = capturedImage.naturalHeight;
        ctx.drawImage(capturedImage, 0, 0);
        
        processCanvas.toBlob(blob => {
            const formData = new FormData();
            formData.append('name', name);
            formData.append('face_image', blob, 'captured_face.jpg');
            
            fetch('/register_face', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    captureModal.hide();
                    loadRegisteredFaces();
                    alert(`Face for ${name} registered successfully!`);
                } else {
                    alert('Error registering face: ' + data.message);
                }
            })
            .catch(error => console.error('Error registering face:', error));
        }, 'image/jpeg', 0.9);
    }
    
    // File upload functions
    function previewUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            uploadName.value = faceName.value || '';
            previewModal.show();
        };
        reader.readAsDataURL(file);
    }
    
    function registerUploadedFace() {
        const name = uploadName.value.trim();
        if (!name) {
            alert('Please enter a name for this face');
            return;
        }
        
        const formData = new FormData();
        formData.append('name', name);
        formData.append('face_image', uploadInput.files[0]);
        
        fetch('/register_face', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                previewModal.hide();
                uploadInput.value = '';
                loadRegisteredFaces();
                alert(`Face for ${name} registered successfully!`);
            } else {
                alert('Error registering face: ' + data.message);
            }
        })
        .catch(error => console.error('Error registering face:', error));
    }
    
    // Database functions
    function loadRegisteredFaces() {
        fetch('/get_registered_faces')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayRegisteredFaces(data.faces);
                    updateFaceCount(data.faces.length);
                } else {
                    console.error('Error loading faces:', data.message);
                }
            })
            .catch(error => console.error('Error loading faces:', error));
    }
    
    function displayRegisteredFaces(faces) {
        facesContainer.innerHTML = '';
        
        if (faces.length === 0) {
            facesContainer.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-person-badge display-3 mb-3"></i>
                    <p>No faces registered yet</p>
                </div>
            `;
            return;
        }
        
        faces.forEach(face => {
            const faceCard = document.createElement('div');
            faceCard.className = 'face-card';
            faceCard.innerHTML = `
                <div class="face-image">
                    <img src="/face_image/${face.id}?t=${new Date().getTime()}" alt="${face.name}">
                </div>
                <div class="face-info">
                    <h5>${face.name}</h5>
                    <button class="btn btn-sm btn-outline-danger delete-face" data-id="${face.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            facesContainer.appendChild(faceCard);
            
            // Add delete event listener
            faceCard.querySelector('.delete-face').addEventListener('click', function() {
                deleteFace(face.id, face.name);
            });
        });
    }
    
    function updateFaceCount(count) {
        faceCount.textContent = count;
        faceCountDisplay.forEach(el => {
            el.textContent = count;
        });
    }
    
    function deleteFace(id, name) {
        if (confirm(`Are you sure you want to delete ${name}?`)) {
            fetch(`/delete_face/${id}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadRegisteredFaces();
                } else {
                    alert('Error deleting face: ' + data.message);
                }
            })
            .catch(error => console.error('Error deleting face:', error));
        }
    }
    
    function confirmResetDatabase() {
        if (confirm('Are you sure you want to delete all registered faces? This cannot be undone.')) {
            fetch('/reset_database', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadRegisteredFaces();
                    alert('Face database has been reset');
                } else {
                    alert('Error resetting database: ' + data.message);
                }
            })
            .catch(error => console.error('Error resetting database:', error));
        }
    }
}); 