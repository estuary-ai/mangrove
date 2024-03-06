import json
from typing import Tuple, Dict, Generator
from loguru import logger
from stt import STTController, WakeUpVoiceDetector, AudioPacket
from tts import TTSController
from storage_manager import StorageManager, write_output


class AssistantController:
    """Main controller for the assistant."""

    def __init__(self, verbose=True, shutdown_bot=False, device=None, name="Traveller"):
        """Initialize the assistant controller.

        Args:
            verbose (bool, optional): Whether to print debug messages. Defaults to True.
            shutdown_bot (bool, optional): Whether to shutdown the bot. Defaults to False.
            name (str, optional): Name of the assistant. Defaults to 'Traveller'.
        """
        self.name = name
        self.verbose = verbose

        self.wake_up_word_detector = WakeUpVoiceDetector(device=device)
        write_output("Initialized WakeUpWordDetector")
        self.stt = STTController(device=device)
        write_output("Initialized STT Controller")

        self.bot = None
        if not shutdown_bot:
            from bot import BotController

            self.bot = BotController()
            write_output("Initialized Bot Controller")

        self.tts = TTSController('pyttsx3')
        # self.tts = TTSController('elevenlabs')
        write_output("Initialized TTS Controller")

        # Debuggers and Auxilarly variables
        self.is_sample_tagging = False
        self.indicator_bool = True
        self.writing_command_audio_threads_list = []
        # self.data_buffer = DataBuffer(frame_size=320)
        self._is_awake = False

    def is_bot_shutdown(self):
        """Check if bot is shutdown

        Returns:
            bool: Whether bot is shutdown
        """
        return self.bot is None

    def is_awake(self):
        """Check if assistant is awake

        Returns:
            bool: Whether assistant is awake
        """
        return self._is_awake

    def startup(self) -> bytes:
        """Startup Upon Connection and return bot voice for introduction

        Returns:
            bytes: audio bytes for introduction
        """
        self.reset_audio_buffers()
        self._initiate_audio_stream()
        bot_voice_bytes = self.read_text(
            "Hello, AI server connection is succesful. "
            # f"This is Your assistant, {self.name}."
        )

        return bot_voice_bytes

    def reset_audio_buffers(self):
        """Resetting session and command audio logging buffers"""
        self.session_audio_buffer = AudioPacket.get_null_packet()
        self.command_audio_buffer = AudioPacket.get_null_packet()

    def _initiate_audio_stream(self):
        """Initiate audio stream for STT"""
        self.stt.create_stream()

    def read_text(self, data: any):
        """Read text using TTS and return audio bytes"""
        # READING VITALS
        # TODO Include transcription in audio bytes sent
        try:
            if isinstance(data, str):
                data = json.loads(str(data))
            audio_bytes = self.tts.get_feature_read_bytes(
                data["feature"], data["values"], data["units"]
            )
        except:
            if isinstance(data, str):
                audio_bytes = self.tts.get_plain_text_read_bytes(data)
            else:
                raise Exception("Only dict/json and str are supported types")
        return audio_bytes

    def feed_audio_stream(self, audio_data):
        """Feed audio stream to STT if awake or WakeUpWordDetector if not awake

        Args:
            audio_data (bytes): Audio data in bytes

        Returns:
            dict: STT response

        """
        audio_packet = AudioPacket(audio_data)
        if self._is_awake:
            if self.is_command_buffer_empty():
                self._initiate_audio_stream()
                write_output("recieving first stream of audio command")

            self.stt_res_buffer = None
            self.command_audio_buffer += audio_packet
            self.session_audio_buffer += (
                audio_packet  # TODO note that this includes is_awake only
            )

            self.stt.feed(audio_packet)
        else:
            self.wake_up_word_detector.feed_audio(audio_packet)

    def is_wake_word_detected(self):
        """Check if wake word is detected and set is_awake accordingly"""
        self._is_awake = self.wake_up_word_detector.is_wake_word_detected()
        if self._is_awake:
            self.wake_up_word_detector.reset_data_buffer()
            self.stt.reset_audio_stream()
        return self._is_awake

    def is_command_buffer_empty(self):
        """Check if command buffer is empty"""
        return len(self.command_audio_buffer) == 0

    def process_audio_buffer(self):
        """Process audio buffer and return STT response"""
        stt_res = self.stt.process_audio_buffer()
        if stt_res:
            StorageManager.write_audio_file(
                self.command_audio_buffer, text=stt_res["text"]
            )
            self.command_audio_buffer = AudioPacket.get_null_packet()
            self._is_awake = False
            print("i am not awake anymore", flush=True)  # TODO remove
        return stt_res

    def clean_up(self):
        """Clean up upon disconnection"""
        self._is_awake = False
        session_audio_buffer, command_audio_buffer = (
            self.session_audio_buffer,
            self.command_audio_buffer,
        )

        self.is_sample_tagging = False
        self.stt.reset_audio_stream()

        if len(command_audio_buffer) > 0:
            StorageManager.play_audio_packet(command_audio_buffer)

        StorageManager.write_audio_file(session_audio_buffer)
        StorageManager.ensure_completion()

    def respond(self, text: str) -> Generator[Tuple[Dict, bytes], None, None]:
        """Respond to user message and return bot response and voice bytes
        # TODO consider adding timeout to this function and remove deprecated logic

        Args:
            text (str): User message

        Returns:
            typing.Tuple[dict, bytes]: Bot response and voice bytes
        """
        if self.bot is None:
            return None

        logger.debug("responding to user message")
        for bot_res in self.bot.respond(text):
            write_output("SENVA: " + str(bot_res))
            bot_texts = bot_res.get("text")

            # TODO it is this way only now for debug
            if bot_res.get('partial'):
                continue

            voice_bytes = None
            if bot_texts:
                logger.trace("creating voice bytes")
                voice_bytes = self.tts.get_plain_text_read_bytes(" ".join(bot_texts))
                logger.trace("voice bytes created")

            # self.check_bot_commands(bot_res)
            # logger.trace("checked bot commands")

            yield bot_res, voice_bytes

        write_output("bot response finished successfully")


    # TODO migrate logic to if procedural step
    def check_bot_commands(self, bot_res):
        def setup_sample_tagging():
            write_output("set in sample tagging")
            self.is_sample_tagging = True
            self.stt.set_sample_tagging_focus()

        def kill_sample_tagging():
            write_output("kill sample tagging")
            self.is_sample_tagging = False
            self.stt.set_regular_focus()
            self.stt.reset_audio_stream()
            # TODO consider also case of termination using exit word

        bot_commands = bot_res.get("commands")
        if bot_commands is not None and len(bot_commands) > 0:
            sample_command = bot_commands[0].get("sample")
            sample_details_command = bot_commands[0].get("sample_details")
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
            write_output("no commands")

    # TODO complete this function
    def process_if_procedural_step(self):
        if self.bot is None:
            return None

        # TODO enclude all types of procedures (i.e UIA Egress Procedure)
        self._process_sample_tagging_if_on()  # TODO

        response = self.bot.process_procedures_if_on()
        if response is None:
            return False
        return response

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
            if not ("over" in stt_res["text"].rstrip()[-30:]):
                return True
            stt_res = self.stt_res_buffer
            self.stt_res_buffer = None
        return False
