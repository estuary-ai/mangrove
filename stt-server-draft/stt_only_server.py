from flask import Flask
from flask_socketio import SocketIO
from STTController import STTController
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app,
    cors_allowed_origins='*',
    cors_credentials=True)

@socketio.on('connect')
def handle_connect():
    print('client connected', flush=True)
    stt.create_stream()
    
@socketio.on('disconnect')
def handle_disconnect():
	print('client disconnected', flush=True)

@socketio.on('stream-data')
def handle_stream_data(data):
    # print('audiostream', len(data))
    results = stt.process_audio_stream(data)
    if results:
        sys.stdout.write('results' +  str(results))
        socketio.emit('recognize', results)
	
@socketio.on('stream-end')
def handle_stream_end():
    sys.stdout.write("\n[end]")
    results = stt.intermediate_decode()
    sys.stdout.write('stream-end' + str(results))
    if results:
        sys.stdout.write('results' + str(results))
        socketio.emit('recognize', results)

@socketio.on('stream-reset')
def handle_stream_reset():
    stt.reset_audio_stream()

if __name__ == '__main__':
    stt = STTController()
    socketio.run(app, host='0.0.0.0', port=4000)