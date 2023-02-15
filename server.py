import os, argparse, json, time
import numpy as np
import sounddevice as sd

from flask import Flask
from flask_socketio import SocketIO, Namespace, emit
from assistant_controller import AssistantController
from storage_manager import StorageManager, write_output

# import tensorflow as tf
# tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
    
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    cors_credentials=True,
    logger=True, 
    engineio_logger=True
)
    

@socketio.on_error_default  # handles all namespaces without an explicit error handler
def default_error_handler(e):
    write_output('error debug', e)
    # stt.reset_audio_stream()
    # # TODO reset anything   
        
class DigitalAssistant(Namespace):
    def __init__(self, namespace):
        super()
        self.namespace = namespace
        self.assistant_controller = AssistantController()
        print("Server is about to be Up and Running..")
        
    def on_connect(self):
        self.assistant_controller.reset_audio_buffers()
        self.assistant_controller.initiate_audio_stream()
        write_output('client connected')
    
    def on_disconnect(self):
        
        session_audio_buffer, command_audio_buffer =\
            self.assistant_controller.get_audio_buffers()
        self.assistant_controller.destroy_stream()

        if len(command_audio_buffer) > 0:
            sd.play(
                np.frombuffer(
                    command_audio_buffer, 
                    dtype=np.int16
                    ),
                16000
            )

        # sd.play(np.frombuffer(session_audio_buffer, dtype=np.int16), 16000)        
        session_id = str(int(time.time()*1000))
        with open(f"sample-audio-binary/{session_id}_binary.txt", mode='wb') as f:
            f.write(session_audio_buffer)
    
    def on_tts_read(self, data):
        try:
            data = json.loads(str(data))
        except:
            raise Exception('Data should be JSON format')
        write_output(f'request to read data {data}')
        audioBytes =\
            self.assistant_controller.read_text(data)
        emit("bot-voice", audioBytes)
    
    def on_stream_wakeup(self, data):
        wakeUpWordDetected =\
            self.assistant_controller.is_wake_word_detected(data)
        if wakeUpWordDetected:
            write_output("detected wakeup word")
            emit('wake-up')    
    
    def on_stream_audio(self, data):
        
        if self.assistant_controller.is_command_buffer_empty():
            write_output("recieving first stream of audio command")
        
        data = bytes(data)
        stt_res = self.assistant_controller.process_audio_stream(data)            
        if stt_res is not None:
            write_output('User: ' + str(stt_res))
            emit('stt-response', stt_res)
        
            is_procedural_step = self.assistant_controller.process_sample_tagging_if_on()
            if is_procedural_step:
                return
        
            bot_res, bot_voice_bytes =\
                self.assistant_controller.respond(stt_res['text'])

            if bot_voice_bytes:
                write_output('emmiting bot-voice')
                emit('bot-voice', bot_voice_bytes)
                
            write_output("emitting bot-response")
            emit('bot-response', bot_res)
    
    def on_reset_audio_stream(self):
        # TODO validate the purpose, so that we might remove
        self.assistant_controller.reset_audio_stream()

    def on_trial(self, data):
        write_output('received trial: ' + data)

socketio.on_namespace(DigitalAssistant('/digital-assistant'))    

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Personal information')
    parser.add_argument('--cpu', dest='cpu', type=bool, default=False, help='Use CPU instead of GPU')
    parser.add_argument('--port', dest='port', type=int, default=4000, help='Use CPU instead of GPU')
    args = parser.parse_args()
    
    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
  
    socketio.run(app, host='0.0.0.0', port=args.port)  