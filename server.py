import os, argparse, json, time
import numpy as np
import sounddevice as sd

from threading import Thread
from flask import Flask
from flask_socketio import SocketIO, Namespace, emit
from stt import WakeUpVoiceDetector, STTController
from bot import BotController
from tts import TTSController

class AIServer(Namespace):
    def __init__(self, namespace):
        super()
        self.namespace = namespace
        print("Initializing WakeUpWordDetector")
        self.wakeUpWordDetector = WakeUpVoiceDetector()
        print("Initializing STT Controller")
        stt = STTController()
        stt.set_regular_focus()
        self.is_sample_tagging = False
        print("Initializing Bot Controller")
        self.bot = BotController()
        print("Initializing TTS Controller")
        self.tts = TTSController()    
        print("Server is about to be Up and Running..")
        
    def on_connect(self):
        self.session_audio_buffer = b""
        self.command_audio_buffer = b""
        self.writing_files_threads_list = []
        self.indicator_bool = True
        self.stt.create_stream()
        self.write_output('client connected')
    
    def on_disconnect(self):
        self.is_sample_tagging = False

        for thread in self.writing_files_threads_list:
            thread.join()

        if len(self.command_audio_buffer) > 0:
            sd.play(
                np.frombuffer(
                    self.command_audio_buffer, 
                    dtype=np.int16
                    ),
                16000
            )

        # sd.play(np.frombuffer(session_audio_buffer, dtype=np.int16), 16000)
        
        session_id = str(int(time.time()*1000))
        with open(f"sample-audio-binary/{session_id}_binary.txt", mode='wb') as f:
            f.write(self.session_audio_buffer)

        # write_output('debug, testing the whole audio of the session')
        self.stt.reset_audio_stream()
        # stt.create_stream()
        # result = stt.process_audio_stream(session_audio_buffer)
        # write_output(result)
    
    def on_tts_read(self, data):
        data = json.loads(str(data))
        self.write_output("request to read data " + str(data))
        audioBytes = self.tts.get_feature_read_bytes(
            data['feature'], data['values'], data['units']
        )
        emit("bot-voice", audioBytes)
    
    def on_stream_wakeup(self, data):
        wakeUpWordDetected =\
            self.wakeUpWordDetector.process_audio_stream(data)
        if wakeUpWordDetected:
            self.write_output("detected wakeup word")
            emit('wake-up')    
    
    def on_stream_audio(self, data):
        def print_feeding_indicator():
            global indicator_bool
            # indicator = "\\" if indicator_bool else  "/"
            self.write_output('=', end="")
            indicator_bool = not indicator_bool
            
        
        def setup_sample_tagging():
            self.write_output('set in sample tagging')
            global is_sample_tagging
            is_sample_tagging = True
            self.stt.set_sample_tagging_focus()

        def kill_sample_tagging():
            self.write_output('kill sample tagging')
            global is_sample_tagging
            is_sample_tagging = False
            self.stt.set_regular_focus()
            self.stt.reset_audio_stream()
            # TODO consider also case of termination using exit word
    
        def check_bot_commands(bot_res):
            bot_commands = bot_res.get('commands')
            if bot_commands is not None and len(bot_commands) > 0:
                sample_command = bot_commands[0].get('sample')
                sample_details_command =  bot_commands[0].get('sample_details')
                if sample_details_command is not None:
                    self.write_output("sample tagging finished successfully")
                    kill_sample_tagging()
                elif sample_command is not None:
                    self.write_output("tagging a sample scenario")
                    setup_sample_tagging()
                elif sample_command is not None and sample_command is False:
                    self.write_output("sample tagging exited")
                    kill_sample_tagging()
                self.write_output('emitting commands ' +  str(bot_res.get('commands')))
            else:
                print('no commands')
            
        def write_to_file(text, command_audio_buffer):
            def write(text, command_audio_buffer):
                with open(f"sample-audio-binary/{text.replace(' ', '_')}_binary.txt", mode='wb') as f:
                    f.write(command_audio_buffer)
            thread = Thread(target=write, args=(text, command_audio_buffer))
            thread.start()
            self.writing_files_threads_list.append(thread)
        
        self.stt_res_buffer = None
        if len(self.command_audio_buffer) == 0:
            self.write_output("recieving first stream of audio command")
        
        data = bytes(data)
        self.command_audio_buffer += data
        self.session_audio_buffer += data

        stt_res = self.stt.process_audio_stream(data)
        if(len(self.command_audio_buffer) % len(data)*10 == 0):
            print_feeding_indicator()
            # write_output(f"={stt.debug_silence_state}=", end="")

        if stt_res is not None:
            self.write_output('User: ' + str(stt_res))
            emit('stt-response', stt_res)
            # stt.unlock_stream()
            
            if self.is_sample_tagging:
                self.write_output("is sample taggin on..")
                # TERMINATION SCHEME BY <OVER> IN SAMPLE-TAGGING
                if self.stt_res_buffer is not None:
                    self.write_output("appending to buffer - sample tagging")
                    self.stt_res_buffer = self.stt._combine_outcomes(
                            [stt_res_buffer, stt_res]
                    )
                self.stt_res_buffer = stt_res
                if not ("over" in stt_res['text'].rstrip()[-30:]):
                    return                
                stt_res = stt_res_buffer
                stt_res_buffer = None
                        
            self.write_to_file(stt_res['text'], command_audio_buffer)
            command_audio_buffer = b""

            bot_res = self.bot.send_user_message(stt_res['text'])
            print('SENVA: ' + str(bot_res))    
            
            bot_texts = bot_res.get('text')
            if bot_texts is not None:
                voice_bytes = self.tts.get_audio_bytes_stream(' '.join(bot_texts))
                self.write_output('emmiting bot-voice')
                emit('bot-voice', voice_bytes)
            else:
                print('no text')

            check_bot_commands(bot_res)

            self.write_output("emitting bot-response")
            emit('bot-response', bot_res)
    
    def on_reset_audio_stream(self):
        self.stt.reset_audio_stream()

    
    def on_trial(self, data):
        self.write_output('received trial: ' + data)
    
    # def on_error(self, err):        
# @socketio.on_error_default  # handles all namespaces without an explicit error handler
# def default_error_handler(e):
#     write_output('error debug', e)
#     stt.reset_audio_stream()
#     # TODO reset anything 
        
    @staticmethod
    def write_output(msg, end='\n'):
        print(str(msg), end=end, flush=True)
    
if __name__ == "__main__":
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret!'
    socketio = SocketIO(
        app,
        cors_allowed_origins='*',
        cors_credentials=True,
        logger=True, 
        engineio_logger=True
    )
    
    parser = argparse.ArgumentParser(description='Personal information')
    parser.add_argument('--cpu', dest='cpu', type=bool, default=False, help='Use CPU instead of GPU')
    parser.add_argument('--port', dest='port', type=int, default=4000, help='Use CPU instead of GPU')
    args = parser.parse_args()
    
    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        
    socketio.on_namespace(AIServer('/aegis-ai'))
    socketio.run(app, host='0.0.0.0', port=args.port)    