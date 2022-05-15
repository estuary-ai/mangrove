from flask import Flask
from flask_socketio import SocketIO
import numpy as np
import sounddevice as sd
from STTController import STTController

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
        sd.play(audio, 16000)
        stt.feed_audio_content(audio)
        result = stt.intermediate_decode()
        write_output("Outcome is")
        write_output(result)
        
    write_output('client disconnected')
 
@socketio.on('stream-data')
def handle_stream_data(data):
    global audio
    audio += data

    # write_output(len(data), end=",")
    # testData = np.frombuffer(audio, dtype=np.int16)

    # is_speech = vad.is_speech(testData, 48000)
    # if is_speech:
    #     process_voice(data)
    # else:
    #     return process_silence(data)

def write_output(msg, end='\n'):
    print(str(msg), end=end, flush=True)
    


if __name__ == '__main__':
    print("Initilizing STT Controller")
    stt = STTController()
    print("Server ia about to be Up and Running..")
    socketio.run(app, host='0.0.0.0', port=4000)    