from typing import Tuple, Dict, Generator
from loguru import logger
from stt import STTController, WakeUpVoiceDetector, AudioPacket
from tts import TTSController
from storage_manager import StorageManager, write_output
from bot import BotController
from enum import IntEnum
from multiprocessing import JoinableQueue

import warnings
# TODO check on this later
warnings.filterwarnings("ignore", category=UserWarning)

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
        tts_endpoint="gtts",
    ):
        """Initialize the assistant controller.

        Args:
            verbose (bool, optional): Whether to print debug messages. Defaults to True.
            name (str, optional): Name of the assistant. Defaults to 'Traveller'.
        """
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
        # self._is_awake = True

    def start(self, server) -> bytes:
        """Start the assistant

        Returns:
            bytes: audio bytes for introduction
        """
        self.reset_audio_buffers()
        self._output_buffer = JoinableQueue()
        self._initiate_audio_stream()
        self.stt.start(server=server)
        self.bot.start(server=server)
        self.tts.start(server=server)

        def _start_looping_thread():
            # complete_segment = {'text': '', 'commands': []}
            while True:
                is_update_occured = False
                transcription = self.stt.receive()
                if transcription:
                    write_output(f"User: {transcription['text']}")
                    self.bot.feed(transcription["text"])
                    is_update_occured = True

                partial_bot_res = self.bot.receive()
                if partial_bot_res:
                    self.tts.feed(partial_bot_res)
                    is_update_occured = True

                partial_voice_bytes = self.tts.receive()
                if partial_voice_bytes:
                    self._output_buffer.put(
                        partial_voice_bytes
                        # TODO note now that this is more than just partial voice bytes
                    )
                    is_update_occured = True

                    # if partial_bot_res.get("start"):
                    #     # TODO do the needed to start a new segment
                    #     complete_segment = {'text': '', 'commands': []}
                    #     write_output("SENVA: ", end='')

                    # if partial_bot_res.get("partial"):
                    #     bot_text = partial_bot_res.get("text")
                    #     write_output(f"{bot_text}", end='')

                    #     assert complete_segment is not None, "complete_segment should not be None"
                    #     complete_segment['commands'] += partial_bot_res['commands']
                    #     complete_segment['text'] += partial_bot_res['text']
                    #     if complete_segment['text'].endswith(('?', '!', '.')):
                    #         # TODO prompt engineer '.' and check other options
                    #         complete_segment['partial'] = True
                    #         self._output_buffer.put(
                    #             (complete_segment, None) # TODO _text_to_voice_segment(complete_segment))
                    #         )
                    #         # NOTE: reset complete_segment
                    #         complete_segment = {'text': '', 'commands': []}

                    #     # if len(complete_segment) > 0:
                    #     #     complete_segment['partial'] = True
                    #     #     yield complete_segment, _text_to_voice_segment(complete_segment)
                    # else:
                    #     # if complete_segment.get('partial'):
                    #     #     # NOTE: this is the last partial response
                    #     #     complete_segment['partial'] = False
                    #     #     logger.debug(f"complete_segment: {complete_segment}")
                    #     #     self._output_buffer.put(
                    #     #         (complete_segment, None) # TODO _text_to_voice_segment(complete_segment))
                    #     #     )
                    #     #     # NOTE: reset complete_segment
                    #     #     complete_segment = {'text': '', 'commands': []}

                    #     # if not partial, then it is a final complete response
                    #     assert partial_bot_res.get('start') is False, "start should be False at this full response stage"
                    #     # a complete response is yielded at the end
                    #     # NOTE: next partial_bot_res.get('start') is gonna be True
                    #     write_output("", end='\n')
                    #     self._output_buffer.put(
                    #         (partial_bot_res, None)
                    #     )

                if not is_update_occured:
                    print('<agent>', end='', flush=True)
                    server.sleep(0.5)

        self._process = server.start_background_task(_start_looping_thread)

    def get_response(self):
        return self._output_buffer.get_nowait()

    def is_awake(self):
        """Check if assistant is awake

        Returns:
            bool: Whether assistant is awake
        """
        return True

    def reset_audio_buffers(self):
        """Resetting session and command audio logging buffers"""
        self.session_audio_buffer = AudioPacket.get_null_packet()
        self.command_audio_buffer = AudioPacket.get_null_packet()

    def _initiate_audio_stream(self):
        """Initiate audio stream for STT"""
        self.stt.create_stream()

    def read_text(self, data: any, as_generator=False):
        """Read text using TTS and return audio bytes"""
        if isinstance(data, str):
            audio_bytes_generator = self.tts.get_plain_text_read_bytes(data)
        else:
            raise Exception("Only dict/json and str are supported types")

        # {
        #         'audio_bytes': audio_packet_dict['audio_bytes'],
        #         'frame_rate': audio_packet_dict['frame_rate'],
        #         'sample_width': audio_packet_dict['sample_width'],
        #         'channels': audio_packet_dict['channels'],
        #     }

        if as_generator:
            return audio_bytes_generator
        else:
            merged_audio_bytes_dict = next(audio_bytes_generator)
            for audio_bytes_dict in audio_bytes_generator:
                merged_audio_bytes_dict['audio_bytes'] += audio_bytes_dict['audio_bytes']
            return merged_audio_bytes_dict
    # def feed_audio_stream(self, audio_data, status: ClientStatus):
    #     """Feed audio stream to STT if awake or WakeUpWordDetector if not awake

    #     Args:
    #         audio_data (bytes): Audio data in bytes

    #     Returns:
    #         dict: STT response

    #     """
    #     audio_packet = AudioPacket(audio_data)
    #     if not self._is_awake and status == ClientStatus.WAITING_FOR_WAKEUP:
    #         self.wake_up_word_detector.feed_audio(audio_packet)

    #     elif status == ClientStatus.WAITING_FOR_COMMAND:
    #         if self.is_command_buffer_empty():
    #             self._initiate_audio_stream()
    #             write_output("recieving first stream of audio command")

    #         self.stt_res_buffer = None
    #         self.command_audio_buffer += audio_packet
    #         self.session_audio_buffer += (
    #             audio_packet  # TODO note that this includes ClientStatus.WAITING_FOR_COMMAND only stream
    #         )

    #         self.stt.feed(audio_packet)

    #     else:
    #         write_output("x", end="")

    def feed_audio_stream(self, audio_data, status: ClientStatus):
        """Feed audio stream to STT if awake or WakeUpWordDetector if not awake

        Args:
            audio_data (bytes): Audio data in bytes

        Returns:
            dict: STT response

        """
        audio_packet = AudioPacket(audio_data)
        if self.is_command_buffer_empty():
            self._initiate_audio_stream()
            write_output("recieving first stream of audio command")

        self.stt_res_buffer = None
        self.command_audio_buffer += audio_packet
        self.session_audio_buffer += (
            audio_packet  # TODO note that this includes ClientStatus.WAITING_FOR_COMMAND only stream
        )

        self.stt.feed(audio_packet)

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
        self._is_awake = True
        session_audio_buffer, command_audio_buffer = (
            self.session_audio_buffer,
            self.command_audio_buffer,
        )
        self.stt.reset_audio_stream()

        if len(command_audio_buffer) > 0:
            StorageManager.play_audio_packet(command_audio_buffer)
        StorageManager.write_audio_file(session_audio_buffer)
        StorageManager.ensure_completion()

    def get_transcription(self):
        """Process audio buffer and return STT response"""
        stt_res = self.stt.get_transcription()
        if stt_res:
            StorageManager.write_audio_file(
                self.command_audio_buffer, text=stt_res["text"]
            )
            self.command_audio_buffer = AudioPacket.get_null_packet()
            # self._is_awake = False
            # logger.debug('Assistant fells asleep.')
        return stt_res

    # def respond(self, text: str) -> Generator[Tuple[Dict, bytes], None, None]:
    #     """Respond to user message and return bot response and voice bytes

    #     Args:
    #         text (str): User message

    #     Returns:
    #         typing.Tuple[dict, bytes]: Bot response and voice bytes
    #     """
    #     def process_segment(chunked_bot_res):
    #         partial_voice_bytes = None
    #         text = chunked_bot_res.get('text')
    #         logger.debug(f"creating voice bytes for {text}")
    #         partial_voice_bytes = self.tts.get_plain_text_read_bytes(text)
    #         logger.trace("voice bytes created")
    #         # self.check_bot_commands(bot_res)
    #         # logger.trace("checked bot commands")
    #         return partial_voice_bytes

    #     logger.debug("responding to user message")
    #     complete_segment = { 'text': '', 'commands': []}
    #     write_output("SENVA: ", end='')
    #     for partial_bot_res in self.bot.respond(text):
    #         if not partial_bot_res.get("partial"):
    #             # if not partial, then it is a final complete response
    #             continue
    #         bot_text = partial_bot_res.get("text")
    #         write_output(f"{bot_text}", end='')
    #         complete_segment['commands'] += partial_bot_res['commands']
    #         complete_segment['text'] += partial_bot_res['text']
    #         if partial_bot_res.get("text").endswith("."):
    #             complete_segment['partial'] = True
    #             yield complete_segment, process_segment(complete_segment)
    #             complete_segment = {'text': '', 'commands': []}

    #     if len(complete_segment) > 0:
    #         complete_segment['partial'] = True
    #         yield complete_segment, process_segment(complete_segment)

    #     # a complete response is yielded at the end
    #     yield partial_bot_res, None
    #     write_output("", end='\n')


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