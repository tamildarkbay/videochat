from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

users = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('user_connected', {'sid': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        username = users[request.sid]
        del users[request.sid]
        emit('user_left', {'username': username, 'sid': request.sid}, broadcast=True)
    print(f'Client disconnected: {request.sid}')

@socketio.on('join')
def handle_join(data):
    username = data['username']
    users[request.sid] = username
    emit('user_joined', {
        'username': username,
        'sid': request.sid,
        'users': users
    }, broadcast=True)
    print(f'{username} ({request.sid}) joined')

@socketio.on('signal')
def handle_signal(data):
    emit('signal', data, to=data['to'])
    print(f'Signal from {data["from"]} to {data["to"]}')

@socketio.on('toggle_audio')
def handle_toggle_audio(data):
    emit('audio_toggled', {
        'sid': request.sid,
        'muted': data['muted']
    }, broadcast=True)

@socketio.on('toggle_video')
def handle_toggle_video(data):
    emit('video_toggled', {
        'sid': request.sid,
        'enabled': data['enabled']
    }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=3333)
