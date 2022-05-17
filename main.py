from flask import Flask
from flask_socketio import SocketIO
from STTController import STTController
from BotController import BotController
from TTSController import TTSController


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

@socketio.on('disconnect')
def handle_disconnect():
    stt.reset_audio_stream()
    write_output('client disconnected')
 
@socketio.on('stream-audio')
def handle_stream_audio(data):
    global audio
    audio += data
    stt_res = stt.process_audio_stream(data)
    if stt_res is not None:
        write_output('User: ' + str(stt_res['text']))
        bot_res = bot.send_user_message(stt_res['text'])
        write_output('SENVA: ' + str(bot_res))
        socketio.emit('bot-response', bot_res)
        
        if bot_res['text'] and len(bot_res['text']) > 0:
            voice_bytes = tts.get_audio_bytes_stream(bot_res['text'])
            socketio.emit('bot-voice', voice_bytes)

@socketio.on('reset-audio-stream')
def handle_reset_audio_stream():
    stt.reset_audio_stream()

@socketio.on('trial')
def handle_trial(data):
    write_output('received trial')
    write_output(data)

def write_output(msg, end='\n'):
    print(str(msg), end=end, flush=True)


if __name__ == '__main__':
    stt = None
    print("Initializing STT Controller")
    stt = STTController(
                    sample_rate=SAMPLE_RATE,
                    model_path='models/ds-model/deepspeech-0.9.3-models',
                    load_scorer=True,
                    silence_threshold=500,
                    vad_aggressiveness=1,
                    frame_size = 320
                )
    print("Initializing Bot Controller")
    bot = BotController()
    print("Initializing TTS Controller")
    tts = TTSController()    
    print("Server is about to be Up and Running..")
    socketio.run(app, host='0.0.0.0', port=4000)    