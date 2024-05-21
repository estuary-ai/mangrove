from typing import Tuple, Dict, Generator
from loguru import logger
from stt import STTController, WakeUpVoiceDetector, AudioPacket
from tts import TTSController
from storage_manager import StorageManager, write_output
from bot import BotController
from enum import IntEnum

class ClientStatus(IntEnum):
    NOT_CONNECTED = 0
    WAITING_FOR_WAKEUP = 1
    WAITING_FOR_COMMAND = 2
    WAITING_FOR_RESPONSE = 3

class AssistantController:
    """Main controller for the assistant."""

    def __init__(
        self,
        verbose=True,
        device=None,
        assistant_name="Marvin",
        tts_endpoint="gtts",
    ):
        """Initialize the assistant controller.

        Args:
            verbose (bool, optional): Whether to print debug messages. Defaults to True.
            name (str, optional): Name of the assistant. Defaults to 'Traveller'.
        """
        self.name = assistant_name
        self.verbose = verbose

        self.wake_up_word_detector = WakeUpVoiceDetector(device=device)
        write_output("Initialized WakeUpWordDetector")
        self.stt = STTController(device=device)
        write_output("Initialized STT Controller")
        self.bot = BotController()
        write_output("Initialized Bot Controller")
        self.tts = TTSController(tts_endpoint)
        write_output("Initialized TTS Controller")

        # Debuggers and Auxilarly variables
        self._is_awake = False

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
        bot_voice_bytes = self.read_text("Welcome, AI server connection is succesful.")
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
        if isinstance(data, str):
            audio_bytes = self.tts.get_plain_text_read_bytes(data)
        else:
            raise Exception("Only dict/json and str are supported types")
        return audio_bytes

    def feed_audio_stream(self, audio_data, status: ClientStatus):
        """Feed audio stream to STT if awake or WakeUpWordDetector if not awake

        Args:
            audio_data (bytes): Audio data in bytes

        Returns:
            dict: STT response

        """
        audio_packet = AudioPacket(audio_data)
        if not self._is_awake and status == ClientStatus.WAITING_FOR_WAKEUP:
            self.wake_up_word_detector.feed_audio(audio_packet)

        elif status == ClientStatus.WAITING_FOR_COMMAND:
            if self.is_command_buffer_empty():
                self._initiate_audio_stream()
                write_output("recieving first stream of audio command")

            self.stt_res_buffer = None
            self.command_audio_buffer += audio_packet
            self.session_audio_buffer += (
                audio_packet  # TODO note that this includes ClientStatus.WAITING_FOR_COMMAND only stream
            )

            self.stt.feed(audio_packet)

        else:
            write_output("x", end="")

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

    def clean_up(self):
        """Clean up upon disconnection"""
        self._is_awake = False
        session_audio_buffer, command_audio_buffer = (
            self.session_audio_buffer,
            self.command_audio_buffer,
        )
        self.stt.reset_audio_stream()

        if len(command_audio_buffer) > 0:
            StorageManager.play_audio_packet(command_audio_buffer)
        StorageManager.write_audio_file(session_audio_buffer)
        StorageManager.ensure_completion()

    def process_audio_buffer(self):
        """Process audio buffer and return STT response"""
        stt_res = self.stt.process_audio_buffer()
        if stt_res:
            StorageManager.write_audio_file(
                self.command_audio_buffer, text=stt_res["text"]
            )
            self.command_audio_buffer = AudioPacket.get_null_packet()
            self._is_awake = False
            logger.debug('Assistant fells asleep.')
        return stt_res

    def respond(self, text: str) -> Generator[Tuple[Dict, bytes], None, None]:
        """Respond to user message and return bot response and voice bytes
        # TODO consider adding timeout to this function and remove deprecated logic

        Args:
            text (str): User message

        Returns:
            typing.Tuple[dict, bytes]: Bot response and voice bytes
        """
        logger.debug("responding to user message")
        bot_res = list(self.bot.respond(text))[-1]
        write_output("SENVA: " + str(bot_res))
        bot_texts = bot_res.get("text")

        voice_bytes = None
        if bot_texts:
            logger.trace("creating voice bytes")
            voice_bytes = self.tts.get_plain_text_read_bytes(" ".join(bot_texts))
            logger.trace("voice bytes created")

        # self.check_bot_commands(bot_res)
        # logger.trace("checked bot commands")
        return bot_res, voice_bytes


    # # TODO migrate logic to if procedural step
    # def check_bot_commands(self, bot_res):
    #     def setup_sample_tagging():
    #         write_output("set in sample tagging")
    #         self.is_sample_tagging = True
    #         self.stt.set_sample_tagging_focus()

    #     def kill_sample_tagging():
    #         write_output("kill sample tagging")
    #         self.is_sample_tagging = False
    #         self.stt.set_regular_focus()
    #         self.stt.reset_audio_stream()
    #         # TODO consider also case of termination using exit word

    #     bot_commands = bot_res.get("commands")
    #     if bot_commands is not None and len(bot_commands) > 0:
    #         sample_command = bot_commands[0].get("sample")
    #         sample_details_command = bot_commands[0].get("sample_details")
    #         if sample_details_command is not None:
    #             write_output("sample tagging finished successfully")
    #             kill_sample_tagging()
    #         elif sample_command is not None:
    #             write_output("tagging a sample scenario")
    #             setup_sample_tagging()
    #         elif sample_command is not None and sample_command is False:
    #             write_output("sample tagging exited")
    #             kill_sample_tagging()
    #         write_output(f'emitting commands {bot_res.get("commands")}')
    #     else:
    #         write_output("no commands")