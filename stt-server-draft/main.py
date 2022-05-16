from flask import Flask
from flask_socketio import SocketIO
import numpy as np
import sounddevice as sd
from STTController import STTController

SAMPLE_RATE = 16000
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app,
    cors_allowed_origins='*',
    cors_credentials=True)

@socketio.on('connect')
def handle_connect():
    global audio
    audio = b""
    stt.create_stream()
    write_output('client connected')

@socketio.on('trial')
def handle_trial(data):
    write_output('received trial')
    write_output(data)

@socketio.on('disconnect')
def handle_disconnect():
    stt.reset_audio_stream()
    write_output('client disconnected')
 
@socketio.on('stream-audio')
def handle_stream_audio(data):
    global audio
    audio += data
    result = stt.process_audio_stream(data)
    if result is not None:
        socketio.emit('response', result)

@socketio.on('reset-audio-stream')
def handle_reset_audio_stream():
    stt.reset_audio_stream()

def write_output(msg, end='\n'):
    print(str(msg), end=end, flush=True)
    

if __name__ == '__main__':
    print("Initializing STT Controller")
    stt = STTController(
                    sample_rate=SAMPLE_RATE,
                    model_path='../models/ds-model/deepspeech-0.9.3-models',
                    load_scorer=True,
                    silence_threshold=500,
                    vad_aggressiveness=1,
                    frame_size = 320
                )
    print("Server is about to be Up and Running..")
    socketio.run(app, host='0.0.0.0', port=4000)    