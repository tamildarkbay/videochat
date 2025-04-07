from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active rooms and participants
rooms = {}

# HTML Templates
entry_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Join Video Call</title>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            color: white;
        }
        .entry-container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            width: 350px;
        }
        h1 {
            margin-top: 0;
            font-weight: 300;
        }
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: none;
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            font-size: 16px;
            box-sizing: border-box;
        }
        input::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        button {
            background: #4a8eff;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin: 15px auto 0;
            transition: all 0.3s ease;
        }
        button:hover {
            background: #3a7bef;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        .error {
            color: #ff6b6b;
            font-size: 14px;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="entry-container">
        <h1>Video Conference</h1>
        <form id="joinForm" action="/call" method="POST" onsubmit="return validateForm()">
            <input type="text" name="username" id="username" placeholder="Your display name" required>
            <div id="error" class="error"></div>
            <button type="submit">
                <i class="material-icons">video_call</i> Join Room
            </button>
        </form>
    </div>
    <script>
        function validateForm() {
            const username = document.getElementById('username').value.trim();
            const errorElement = document.getElementById('error');
            
            if (username.length < 3) {
                errorElement.textContent = 'Name must be at least 3 characters';
                return false;
            }
            
            if (username.length > 20) {
                errorElement.textContent = 'Name must be less than 20 characters';
                return false;
            }
            
            errorElement.textContent = '';
            return true;
        }
    </script>
</body>
</html>
"""

call_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Video Call - {{username}}</title>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: 'Arial', sans-serif;
            background: #1a1a1a;
            color: white;
            overflow: hidden;
            height: 100vh;
        }
        .video-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1rem;
            padding: 1rem;
            height: calc(100vh - 80px);
            overflow-y: auto;
        }
        .video-frame {
            position: relative;
            background: #333;
            border-radius: 8px;
            overflow: hidden;
            transition: all 0.3s ease;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
            aspect-ratio: 16/9;
        }
        .video-frame video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        .video-frame.speaking {
            box-shadow: 0 0 20px #4a8eff;
            transform: scale(1.02);
        }
        .name-tag {
            position: absolute;
            bottom: 8px;
            left: 8px;
            background: rgba(0,0,0,0.5);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 14px;
        }
        .mute-icon {
            position: absolute;
            top: 8px;
            right: 8px;
            color: #ff4a4a;
            background: rgba(0,0,0,0.5);
            border-radius: 50%;
            padding: 4px;
            font-size: 16px;
        }
        .controls {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 1rem;
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 10px;
            border-radius: 50px;
            z-index: 100;
        }
        .control-button {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: none;
            background: #4a8eff;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }
        .control-button:hover {
            transform: scale(1.1);
        }
        .control-button.danger {
            background: #ff4a4a;
        }
        .control-button.active {
            background: #4CAF50;
        }
        .participant-count {
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 8px 12px;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            z-index: 100;
        }
        .participant-list {
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            background: rgba(0,0,0,0.8);
            padding: 10px;
            border-radius: 8px;
            min-width: 150px;
            max-height: 300px;
            overflow-y: auto;
        }
        .participant-count:hover .participant-list {
            display: block;
        }
        .participant-list div {
            padding: 5px 0;
            border-bottom: 1px solid #444;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        #localVideo {
            transform: scaleX(-1);
        }
        .empty-room {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
            color: #888;
            font-size: 18px;
        }
        @media (max-width: 768px) {
            .video-container {
                grid-template-columns: 1fr;
            }
            .controls {
                bottom: 10px;
                padding: 8px;
            }
            .control-button {
                width: 40px;
                height: 40px;
                font-size: 14px;
            }
        }
    </style>
</head>
<body>
    <div class="video-container" id="videoContainer">
        <!-- Videos will be added here dynamically -->
    </div>
    
    <div class="controls">
        <button id="micToggle" class="control-button active">
            <i class="material-icons">mic</i>
        </button>
        <button id="cameraToggle" class="control-button active">
            <i class="material-icons">videocam</i>
        </button>
        <button id="screenShare" class="control-button">
            <i class="material-icons">screen_share</i>
        </button>
        <button id="leaveButton" class="control-button danger">
            <i class="material-icons">call_end</i>
        </button>
    </div>
    
    <div class="participant-count" id="participantCount">
        <i class="material-icons">people</i>
        <span id="count">1</span>
        <div class="participant-list" id="participantList"></div>
    </div>
    
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io();
        const videoContainer = document.getElementById('videoContainer');
        const participantList = document.getElementById('participantList');
        const participantCount = document.getElementById('count');
        
        const username = '{{username}}';
        const roomId = '{{room_id}}';
        const userId = 'user_' + Math.random().toString(36).substring(2, 9);
        
        let localStream;
        let peers = {};
        let isScreenSharing = false;
        let screenStream;
        
        // Initialize media and connection
        async function init() {
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ 
                    video: true, 
                    audio: true 
                });
                
                addLocalVideo();
                setupEventListeners();
                
                // Join the room with user details
                socket.emit('join', { 
                    username, 
                    roomId, 
                    userId 
                });
                
            } catch (err) {
                console.error("Error accessing media devices:", err);
                alert("Could not access camera and microphone. Please check permissions.");
            }
        }
        
        function addLocalVideo() {
            const video = document.createElement('video');
            video.id = 'localVideo';
            video.srcObject = localStream;
            video.muted = true;
            video.autoplay = true;
            video.playsInline = true;
            
            const container = createVideoContainer(video, 'You (${username})', true);
            videoContainer.appendChild(container);
        }
        
        function createVideoContainer(video, name, isLocal = false) {
            const container = document.createElement('div');
            container.className = 'video-frame';
            container.dataset.userId = isLocal ? 'local' : userId;
            
            const nameTag = document.createElement('div');
            nameTag.className = 'name-tag';
            nameTag.textContent = name;
            
            const muteIcon = document.createElement('i');
            muteIcon.className = 'material-icons mute-icon';
            muteIcon.textContent = 'mic_off';
            muteIcon.style.display = 'none';
            
            container.appendChild(video);
            container.appendChild(nameTag);
            container.appendChild(muteIcon);
            
            return container;
        }
        
        function setupEventListeners() {
            // Mic toggle
            document.getElementById('micToggle').addEventListener('click', () => {
                const micOn = localStream.getAudioTracks()[0].enabled;
                localStream.getAudioTracks()[0].enabled = !micOn;
                socket.emit('mute-status', { 
                    userId, 
                    isMuted: !micOn 
                });
                updateMicIcon('local', !micOn);
                updateButtonState('micToggle', !micOn);
            });
            
            // Camera toggle
            document.getElementById('cameraToggle').addEventListener('click', () => {
                const camOn = localStream.getVideoTracks()[0].enabled;
                localStream.getVideoTracks()[0].enabled = !camOn;
                updateCameraIcon('local', !camOn);
                updateButtonState('cameraToggle', !camOn);
            });
            
            // Screen share
            document.getElementById('screenShare').addEventListener('click', toggleScreenShare);
            
            // Leave button
            document.getElementById('leaveButton').addEventListener('click', () => {
                window.location.href = '/';
            });
            
            // Socket events
            socket.on('user-connected', (data) => {
                addParticipant(data.userId, data.username);
                updateParticipantCount();
            });
            
            socket.on('user-disconnected', (disconnectedUserId) => {
                removeParticipant(disconnectedUserId);
                updateParticipantCount();
            });
            
            socket.on('mute-status', (data) => {
                updateMicIcon(data.userId, data.isMuted);
            });
            
            socket.on('participant-list', (users) => {
                updateParticipantList(users);
                updateParticipantCount();
            });
        }
        
        async function toggleScreenShare() {
            try {
                if (!isScreenSharing) {
                    screenStream = await navigator.mediaDevices.getDisplayMedia({ 
                        video: true,
                        audio: false 
                    });
                    
                    // Replace video track
                    const videoTrack = screenStream.getVideoTracks()[0];
                    localStream.getVideoTracks()[0].stop();
                    localStream.removeTrack(localStream.getVideoTracks()[0]);
                    localStream.addTrack(videoTrack);
                    
                    // Update UI
                    document.querySelector('#localVideo').srcObject = localStream;
                    isScreenSharing = true;
                    updateButtonState('screenShare', true);
                    
                    // Handle when user stops sharing
                    videoTrack.onended = () => toggleScreenShare();
                    
                } else {
                    // Switch back to camera
                    const cameraStream = await navigator.mediaDevices.getUserMedia({ 
                        video: true 
                    });
                    const videoTrack = cameraStream.getVideoTracks()[0];
                    
                    // Replace screen track with camera
                    screenStream.getTracks().forEach(track => track.stop());
                    localStream.removeTrack(localStream.getVideoTracks()[0]);
                    localStream.addTrack(videoTrack);
                    
                    // Update UI
                    document.querySelector('#localVideo').srcObject = localStream;
                    isScreenSharing = false;
                    updateButtonState('screenShare', false);
                }
            } catch (err) {
                console.error('Screen sharing error:', err);
            }
        }
        
        function addParticipant(userId, name) {
            // In a real app, you would create a video element for the remote stream
            // For this demo, we'll create a placeholder with random speaking detection
            const video = document.createElement('video');
            video.autoplay = true;
            video.playsInline = true;
            
            // Simulate video stream with color placeholder
            const canvas = document.createElement('canvas');
            canvas.width = 640;
            canvas.height = 480;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = `hsl(${Math.random() * 360}, 70%, 50%)`;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            const stream = canvas.captureStream();
            video.srcObject = stream;
            
            const container = createVideoContainer(video, name);
            container.dataset.userId = userId;
            videoContainer.appendChild(container);
            
            // Simulate speaking detection for demo purposes
            setInterval(() => {
                const shouldGlow = Math.random() > 0.7;
                container.classList.toggle('speaking', shouldGlow);
            }, 2000 + Math.random() * 3000);
        }
        
        function removeParticipant(userId) {
            const videoElement = document.querySelector(`.video-frame[data-user-id="${userId}"]`);
            if (videoElement) {
                videoElement.remove();
            }
        }
        
        function updateMicIcon(userId, isMuted) {
            const container = document.querySelector(`.video-frame[data-user-id="${userId}"]`);
            if (container) {
                const icon = container.querySelector('.mute-icon');
                icon.style.display = isMuted ? 'block' : 'none';
            }
        }
        
        function updateCameraIcon(userId, isOff) {
            if (userId === 'local') {
                const camButton = document.getElementById('cameraToggle');
                const icon = camButton.querySelector('i');
                icon.textContent = isOff ? 'videocam_off' : 'videocam';
            }
        }
        
        function updateButtonState(buttonId, isActive) {
            const button = document.getElementById(buttonId);
            if (isActive) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        }
        
        function updateParticipantList(users) {
            participantList.innerHTML = '';
            
            for (const [id, user] of Object.entries(users)) {
                const participant = document.createElement('div');
                participant.textContent = user.username;
                
                if (user.muted) {
                    const muteIcon = document.createElement('i');
                    muteIcon.className = 'material-icons';
                    muteIcon.textContent = 'mic_off';
                    muteIcon.style.fontSize = '14px';
                    muteIcon.style.marginLeft = '5px';
                    participant.appendChild(muteIcon);
                }
                
                participantList.appendChild(participant);
            }
        }
        
        function updateParticipantCount() {
            const count = document.querySelectorAll('.video-frame:not([data-user-id="local"])').length + 1;
            participantCount.textContent = count;
        }
        
        // Start the app when DOM is loaded
        document.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>
"""

# Flask Routes
@app.route('/')
def index():
    return entry_html

@app.route('/call', methods=['GET', 'POST'])
def call():
    if request.method == 'GET':
        return redirect(url_for('index'))
    
    username = request.form.get('username', 'Anonymous').strip()
    if len(username) < 3 or len(username) > 20:
        return redirect(url_for('index'))
    
    room_id = 'default_room'
    return call_html.replace('{{username}}', username).replace('{{room_id}}', room_id)

# Socket.IO Events
@socketio.on('join')
def handle_join(data):
    username = data['username']
    room_id = data['roomId']
    user_id = data['userId']
    
    join_room(room_id)
    
    if room_id not in rooms:
        rooms[room_id] = {}
    
    rooms[room_id][user_id] = {
        'username': username,
        'muted': False
    }
    
    # Send updated participant list to everyone in the room
    emit('participant-list', rooms[room_id], to=room_id)
    
    # Notify others about the new user (except sender)
    emit('user-connected', {
        'userId': user_id,
        'username': username
    }, to=room_id, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    for room_id, users in rooms.items():
        if request.sid in users:
            user_id = request.sid
            del users[user_id]
            emit('user-disconnected', user_id, to=room_id)
            emit('participant-list', rooms[room_id], to=room_id)
            break

@socketio.on('mute-status')
def handle_mute_status(data):
    room_id = next((rid for rid, users in rooms.items() if data['userId'] in users), None)
    if room_id:
        rooms[room_id][data['userId']]['muted'] = data['isMuted']
        emit('mute-status', data, to=room_id)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5050, debug=True)