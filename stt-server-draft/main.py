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
    global audio
    audio = np.frombuffer(audio, dtype=np.int16)
    write_output('audio to be played is of length ' + str(len(audio)))
    if len(audio) > 0:
        sd.play(audio, SAMPLE_RATE)
        stt.create_stream()
        stt.feed_audio_content(audio)
        result = stt.intermediate_decode()
        write_output("final Outcome is")
        write_output(result)
        
    write_output('client disconnected')
 
@socketio.on('stream-data')
def handle_stream_data(data):
    global audio
    audio += data
    result = stt.process_audio_stream(data)
    if result is not None:
        socketio.emit('recognize', result)

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
    print("Server ia about to be Up and Running..")
    socketio.run(app, host='0.0.0.0', port=4000)    