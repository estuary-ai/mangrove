import time
import json
import typing
from stt import STTController, WakeUpVoiceDetector, AudioPacket
from bot import BotController
from tts import TTSController
from storage_manager import StorageManager, write_output


DEFINED_PAUSE_PERIOD=0.5 # in seconds pause between stt responses

class AssistantController:
    
    def __init__(self, verbose=True, shutdown_bot=False):
        self.verbose = verbose
        self.wakeUpWordDetector = WakeUpVoiceDetector()
        write_output("Initialized WakeUpWordDetector")
        
        self.stt = STTController()
        write_output("Initialized STT Controller")
        # self.stt.set_regular_focus()
        # print('Set STT on regular focus')
        
        self.bot = None
        if not shutdown_bot:
            self.bot = BotController()
            write_output("Initialized Bot Controller")
        
        self.tts = TTSController()    
        write_output("Initialized TTS Controller")
        
        # Debuggers and Auxilarly variables
        self.is_sample_tagging = False
        self.indicator_bool = True
        self.writing_command_audio_threads_list = []        
        # self.data_buffer = DataBuffer(frame_size=320)
        self.is_awake = False

    def startup(self) -> bytes:
        """Startup Upon Connection and return bot voice for introduction

        Returns:
            bytes: audio bytes for introduction
        """
        self.reset_audio_buffers()
        self.initiate_audio_stream()
        bot_voice_bytes = self.read_text(
            "Hello, AI server connection is succesful. "
            "This is Your assistant, Senva.",
            plain_text=True
        )
        return bot_voice_bytes
        
    def reset_audio_buffers(self):
        """Resetting session and command audio logging buffers
        """
        self.session_audio_buffer = AudioPacket.get_null_packet()
        self.command_audio_buffer = AudioPacket.get_null_packet()
    
    def initiate_audio_stream(self):
        self.stt.create_stream()
        
    def read_text(self, data: any, plain_text=False):
        if plain_text:
            audio_bytes = self.tts.get_plain_text_read_bytes(data)
        else:
            # READING VITALS
            # TODO Include transcription in audio bytes sent
            try:
                if isinstance(data, str):
                    data = json.loads(str(data))
                audio_bytes = self.tts.get_feature_read_bytes(
                    data['feature'], data['values'], data['units']
                )
            except:
                raise Exception('Data should be JSON format')
            raise Exception("Only dict/json and str are supported types")
        return audio_bytes
    
    def feed_audio_stream(self, audio_data):
        def _feed_audio_stream_wakeup(audio_packet):
            self.wakeUpWordDetector.feed_audio(audio_packet)

        def _feed_audio_stream_command(audio_packet):
            if self.is_command_buffer_empty():
                self.initiate_audio_stream()
                write_output("recieving first stream of audio command")
                
            self.stt_res_buffer = None
            self.command_audio_buffer += audio_packet
            self.session_audio_buffer += audio_packet
            self.stt.process_audio_stream(audio_packet)
        
        audio_packet = AudioPacket(audio_data)
        if self.is_awake:
            _feed_audio_stream_command(audio_packet)
        else:
            _feed_audio_stream_wakeup(audio_packet)
            
    def is_wake_word_detected(self):
        return self.wakeUpWordDetector.process_audio_stream()
    
    def is_command_buffer_empty(self):
        return len(self.command_audio_buffer) == 0
        
    def process_audio_buffer(self):
        stt_res = self.stt.process_audio_buffer()
        if stt_res:
            StorageManager.write_audio_file(
                self.command_audio_buffer,
                text=stt_res['text']
            )
            self.command_audio_buffer = AudioPacket.get_null_packet()
        return stt_res                        
    
    def clean_up(self):
        """Clean up upon disconnection and delegate logging
        """
        self.is_awake = False
        session_audio_buffer, command_audio_buffer =\
            self.session_audio_buffer, self.command_audio_buffer
            
        self.is_sample_tagging = False
        self.stt.reset_audio_stream()

        if len(command_audio_buffer) > 0:
            StorageManager.play_audio_packet(command_audio_buffer)
            
        StorageManager.write_audio_file(
            session_audio_buffer,
            include_session_id=True
        )
        
        StorageManager.ensure_completion()

    def respond(self, text: str) -> typing.Tuple[dict, bytes]:
        if self.bot is None:
            breakpoint()
            return None, None
        bot_res = self.bot.send_user_message(text)
        write_output('SENVA: ' + str(bot_res))  
        bot_texts = bot_res.get('text')
        voice_bytes = None
        if bot_texts:
            voice_bytes = self.tts.get_plain_text_read_bytes(
                ' '.join(bot_texts)
            )

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
            write_output(f'emitting commands {bot_res.get("commands")}')
        else:
            write_output('no commands')
    
    def process_if_procedural_step(self):
        # TODO enclude all types of procedures (i.e UIA Egress Procedure)
        self._process_sample_tagging_if_on()
        
        return self.bot.process_procedures_if_on()


        
    def _process_sample_tagging_if_on(self):
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