import os, argparse, json, time
import sounddevice as sd
import numpy as np

from flask import Flask
from flask_socketio import SocketIO, Namespace, emit
from assistant_controller import AssistantController
from storage_manager import StorageManager, write_output
from multiprocessing import Lock
# import tracemalloc
# tracemalloc.start()

# log.basicConfig(filename='output.log', level=log.INFO)

# import tensorflow as tf
# tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
    
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    cors_credentials=True,
    # async_mode='gevent'
    # logger=True, engineio_logger=True
)

# @socketio.on_error_default  # handles all namespaces without an explicit error handler
# def default_error_handler(e):
#     write_output(f'Error debug {e}')
#     # stt.reset_audio_stream()
#     # # TODO reset anything   
        
class DigitalAssistant(Namespace):
    def __init__(self, namespace):
        super()
        self.namespace = namespace
        self.assistant_controller = AssistantController()
        
        self.is_awake = False
        self.lock = Lock()
        
        socketio.start_background_task(self.bg_responding_task)
        
        write_output("Server is about to be Up and Running..")
        
    def on_connect(self):
        self.assistant_controller.reset_audio_buffers()
        self.assistant_controller.initiate_audio_stream()
        write_output('client connected\n')
        bot_voice_bytes = self.assistant_controller.read_text(
            "Hello, AI server connection is succesful. This is Your assistant, Senva."
        )
        if bot_voice_bytes:
            write_output('emmiting bot_voice')
            socketio.emit('bot_voice', bot_voice_bytes)
            
    
    def on_disconnect(self):
        write_output('client disconnected\n')
        # self.assistant_controller.clean()
        session_audio_buffer, command_audio_buffer =\
            self.assistant_controller.get_audio_buffers()
        # TODO Write meta data too
        self.assistant_controller.destroy_stream()

        if len(command_audio_buffer) > 0:
            sd.play(
                np.frombuffer(
                    command_audio_buffer.bytes, 
                    dtype=np.int16
                    ),
                16000
            )

        # sd.play(np.frombuffer(session_audio_buffer, dtype=np.int16), 16000)        
        session_id = str(int(time.time()*1000))
        with open(f"sample-audio-binary/{session_id}_binary.txt", mode='wb') as f:
            f.write(session_audio_buffer.bytes)
    
    def on_tts_read(self, data):
        try:
            data = json.loads(str(data))
        except:
            raise Exception('Data should be JSON format')
        write_output(f'request to read data {data}')
        # TODO Convert into json format response including transcription
        audio_bytes =\
            self.assistant_controller.read_text(data)
        emit("bot_voice", audio_bytes)
    
    def on_stream_wakeup(self, data):
        start = time.time()
        wakeUpWordDetected =\
            self.assistant_controller.is_wake_word_detected(data)
        write_output(f'took {time.time() - start}', end='\r')
        if wakeUpWordDetected and not self.is_awake:
            write_output("detected wakeup word")
            emit('wake_up')    
            self.is_awake = True
    
    def on_stream_audio(self, data):
        with self.lock:
            if not self.is_awake:
                # Instead buffer in main buffer but dont keep like now
                return
            if self.assistant_controller.is_command_buffer_empty():
                self.assistant_controller.initiate_audio_stream()
                write_output("recieving first stream of audio command")
            
            # Feeding in audio stream
            self.assistant_controller.process_audio_stream(data)            
        
    def on_reset_audio_stream(self):
        # TODO validate the purpose, so that we might remove
        write_output('on reset audio stream')
        self.assistant_controller.reset_audio_stream()

    def on_trial(self, data):
        write_output(f'received trial: {data}')

    def bg_responding_task(self):
        # READ BUFFER AND EMIT AS NEEDED
        counter = 0
        while True:
            socketio.sleep(0.5)
            counter += 1
            if self.is_awake:
                self.apply_communication_logic(counter)
            
            
    def apply_communication_logic(self, counter):
        with self.lock:
            write_output(f'is awake {counter}: {self.is_awake}', end='\r')
            
            stt_res = self.assistant_controller.process_audio_buffer()
            if stt_res is None:
                return
            
            self.is_awake = False
            write_output(f'\nUser: {stt_res}')
            socketio.emit('stt_response', stt_res)
        
            is_procedural_step = self.assistant_controller.process_sample_tagging_if_on()
            if is_procedural_step:
                return
        
            bot_res, bot_voice_bytes =\
                self.assistant_controller.respond(stt_res['text'])

            # Include timestamps
            if bot_voice_bytes:
                write_output('emmiting bot_voice')
                socketio.emit('bot_voice', bot_voice_bytes)
            
            if bot_res: # None only if bot is shutdown
                write_output("emitting bot_response")
                socketio.emit('bot_response', bot_res)
            else:
                socketio.emit('bot_repsonse', {
                    'msg': 'bot is shutdown' 
                })

            
        
# @socketio.on('message')
# def handle_message(data):
#     print('received message: ' + data)
    
if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Digital Assistant Endpoint')
    parser.add_argument('--cpu', dest='cpu', type=bool, default=False, help='Use CPU instead of GPU')
    parser.add_argument('--port', dest='port', type=int, default=4000, help='Port number')
    args = parser.parse_args()

    digital_assistant = DigitalAssistant('/')
    socketio.on_namespace(digital_assistant)    

    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    write_output(f'Running on port {args.port}')
    
    
    socketio.run(
        app, host='0.0.0.0',
        port=args.port, 
        use_reloader=False
    )  