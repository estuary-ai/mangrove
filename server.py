import os, argparse
from flask import Flask
from flask_socketio import SocketIO, Namespace, emit
from assistant_controller import AssistantController
from storage_manager import StorageManager, write_output
from multiprocessing import Lock

# log.basicConfig(filename='output.log', level=log.INFO)

import tensorflow as tf
print(tf.config.list_physical_devices('GPU'))
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
    
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
    def __init__(self, namespace, assistant_name='SENVA'):
        super()
        self.namespace = namespace
        self.assistant_controller = AssistantController(name=assistant_name)
        self.lock = Lock()        
        
        self.responding_task = socketio.start_background_task(self.bg_responding_task)
        write_output("Server is about to be Up and Running..")
        
    def on_connect(self):
        write_output('client connected\n')
        bot_voice_bytes = self.assistant_controller.startup()
        if bot_voice_bytes:
            write_output('emmiting bot_voice')
            socketio.emit('bot_voice', bot_voice_bytes)
    
    def on_disconnect(self):
        write_output('client disconnected\n')
        with self.lock:
            self.assistant_controller.clean_up()    
    
    def on_tts_read(self, data):
        write_output(f'request to read data {data}')
        audio_bytes = self.assistant_controller.read_text(data)
        emit("bot_voice", audio_bytes)
    
    def on_stream_audio(self, audio_data):
        with self.lock:
            # Feeding in audio stream
            self.assistant_controller.feed_audio_stream(audio_data) 
        
    def on_trial(self, data):
        write_output(f'received trial: {data}')
    
    def on_stream_text(self, command):
        if not isinstance(command, str):
            raise Exception("Datatype is not supported")
        # breakpoint()
        command = {"text": command}
        write_output(f'\nUser: {command}')
        self.bot_respond(command)
        
        
        

    def bg_responding_task(self):
        # READ BUFFER AND EMIT AS NEEDED
        # counter = 0
        while True:
            socketio.sleep(0.01)
            # counter += 1
            with self.lock:
                if self.assistant_controller.is_awake:
                    # write_output(f'is awake {counter}: {self.assistant_controller.is_awake}', end='\r')
                    self.apply_communication_logic()
                    # TODO introduce timeout
                else:
                    # start = time.time()
                    wakeUpWordDetected =\
                        self.assistant_controller.is_wake_word_detected()
                    # write_output(f'took {time.time() - start}', end='\r')
                    if wakeUpWordDetected:
                        write_output("detected wakeup word")
                        socketio.emit('wake_up')    
                        self.assistant_controller.is_awake = True
                
    def apply_communication_logic(self):        
        stt_res = self.assistant_controller.process_audio_buffer()
        if stt_res is None:
            return
        self.assistant_controller.is_awake = False
   
        write_output(f'\nUser: {stt_res}')
        socketio.emit('stt_response', stt_res)
    
        # TODO check logic of is_awake
        is_procedural_step = self.assistant_controller.process_if_procedural_step()
        if is_procedural_step:
            return
        
        self.bot_respond(stt_res)
    
    def bot_respond(self, stt_res):
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
            write_output('shutting down bot')
            socketio.emit('bot_repsonse', {
                'msg': 'bot is shutdown' 
            })


if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Digital Assistant Endpoint')
    parser.add_argument('--cpu', dest='cpu', type=bool, default=False, help='Use CPU instead of GPU')
    parser.add_argument('--port', dest='port', type=int, default=4000, help='Port number')
    args = parser.parse_args()

    # TODO use digital_assistant_name to set introduction msg
    digital_assistant_name = 'Habibi'
    digital_assistant = DigitalAssistant('/', assistant_name=digital_assistant_name)
    socketio.on_namespace(digital_assistant)    

    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        
    # host_ip_address = socket.gethostbyname(socket.gethostname())
    write_output(f'\nYour Digital Assistant {digital_assistant_name} running on port {args.port}')
    write_output('Hints:')
    write_output('1. Run "ipconfig" in your terminal and use Wireless LAN adapter Wi-Fi IPv4 Address')
    write_output('2. Ensure your client is connected to the same WIFI connection')
    write_output('3. Ensure firewall shields are down in this particular network type with python')
    write_output('4. Ensure your client microphone is not used by any other services such as windows speech-to-text api')
    write_output('Fight On!')
    
    socketio.run(
        app, host='0.0.0.0',
        port=args.port, 
        use_reloader=False
    )  