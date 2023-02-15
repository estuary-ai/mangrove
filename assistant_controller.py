import json
import typing
from stt import WakeUpVoiceDetector, STTController
from bot import BotController
from tts import TTSController
from threading import Thread
from storage_manager import StorageManager, write_output

class AssistantController:
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.wakeUpWordDetector = WakeUpVoiceDetector()
        print("Initialized WakeUpWordDetector")
        self.stt = STTController()
        print("Initialized STT Controller")
        self.stt.set_regular_focus()
        print('Set STT on regular focus')
        self.bot = BotController()
        print("Initialized Bot Controller")
        self.tts = TTSController()    
        print("Initialized TTS Controller")
        
        # Debuggers and Auxilarly variables
        self.is_sample_tagging = False
        self.indicator_bool = True
        self.writing_command_audio_threads_list = []


    def reset_audio_buffers(self):
        self.session_audio_buffer = b""
        self.command_audio_buffer = b""
    
    def get_audio_buffers(self):
        return self.session_audio_buffer, self.command_audio_buffer
    
    def initiate_audio_stream(self):
        self.stt.create_stream()
        
    def destroy_stream(self):
        StorageManager.ensure_completion()
        self.is_sample_tagging = False
        self.stt.reset_audio_stream()
        
    def reset_audio_stream(self):
        self.stt.reset_audio_stream()
        
    def read_text(self, data: dict):
        audioBytes = self.tts.get_feature_read_bytes(
            data['feature'], data['values'], data['units']
        )
        return audioBytes
    
    def is_wake_word_detected(self, data):
        return self.wakeUpWordDetector.process_audio_stream(data)
    
    def is_command_buffer_empty(self):
        return len(self.command_audio_buffer) == 0
        
    def process_audio_stream(self, data: bytes):
        self.stt_res_buffer = None
        self.command_audio_buffer += data
        self.session_audio_buffer += data
        stt_res = self.stt.process_audio_stream(data)
        
        if self.verbose:
            if(len(self.command_audio_buffer) % len(data)*10 == 0):
                self.print_feeding_indicator()
                
        StorageManager.write_audio_file(
            stt_res['text'],
            command_audio_buffer
        )
        command_audio_buffer = b""

                
    def print_feeding_indicator(self):
        # indicator = "\\" if indicator_bool else  "/"
        write_output('=', end="")
        self.indicator_bool = not self.indicator_bool
        
    def process_sample_tagging_if_on(self):
        if self.is_sample_tagging:
            write_output("is sample taggin on..")
            # TERMINATION SCHEME BY <OVER> IN SAMPLE-TAGGING
            if self.stt_res_buffer is not None:
                # TODO check if this is even reachable!
                write_output("appending to buffer - sample tagging")
                self.stt_res_buffer = self.stt._combine_outcomes(
                    [self.stt_res_buffer, stt_res]
                )
            self.stt_res_buffer = stt_res
            if not ("over" in stt_res['text'].rstrip()[-30:]):
                return True                
            stt_res = self.stt_res_buffer
            self.stt_res_buffer = None
            return False
        
    def respond(self, text: str) -> typing.Tuple[dict, bytes]:
        bot_res = self.bot.send_user_message(text)
        print('SENVA: ' + str(bot_res))  
        bot_texts = bot_res.get('text')
        voice_bytes = None
        if bot_texts is not None:
            voice_bytes = self.tts.get_audio_bytes_stream(' '.join(bot_texts))
    
        self.check_bot_commands(bot_res)

        return bot_res, voice_bytes
    
    def check_bot_commands(self, bot_res):
        def setup_sample_tagging():
            write_output('set in sample tagging')
            self.is_sample_tagging = True
            self.stt.set_sample_tagging_focus()

        def kill_sample_tagging():
            write_output('kill sample tagging')
            self.is_sample_tagging = False
            self.stt.set_regular_focus()
            self.stt.reset_audio_stream()
            # TODO consider also case of termination using exit word

        bot_commands = bot_res.get('commands')
        if bot_commands is not None and len(bot_commands) > 0:
            sample_command = bot_commands[0].get('sample')
            sample_details_command =  bot_commands[0].get('sample_details')
            if sample_details_command is not None:
                write_output("sample tagging finished successfully")
                kill_sample_tagging()
            elif sample_command is not None:
                write_output("tagging a sample scenario")
                setup_sample_tagging()
            elif sample_command is not None and sample_command is False:
                write_output("sample tagging exited")
                kill_sample_tagging()
            write_output('emitting commands ' +  str(bot_res.get('commands')))
        else:
            print('no commands')
    