from stt import STTController
from stt.wakeup_word.wakeup_word_detector import WakeUpVoiceDetector
from core import AudioPacket
from tts import TTSController
from storage_manager import StorageManager, write_output
from bot import BotController
from multiprocessing import JoinableQueue
from core import TextPacket, AudioPacket, AudioBuffer

import warnings
# TODO check on this later
warnings.filterwarnings("ignore", category=UserWarning)

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

        self.startup_audiopacket: AudioPacket = None

    def on_connect(self, host):
        if self.startup_audiopacket:
            from copy import deepcopy
            host.emit_bot_voice(deepcopy(self.startup_audiopacket))

    def start(
        self,
        server,
        welcome_msg="Welcome, AI server connection is succesful."
    ):
        """Start the assistant
        """
        self.reset_audio_buffers()
        self._output_buffer = JoinableQueue()
        self.stt.start(server=server)
        self.bot.start(server=server)
        self.tts.start(server=server)

        if welcome_msg:
            self.startup_audiopacket = self.tts.read(welcome_msg, as_generator=False)

        def _start_looping_thread():
            while True:
                is_update_occured = False

                transcription: TextPacket = self.stt.receive()
                if transcription:
                    write_output(f"User: {transcription.text}")
                    self.bot.feed(transcription)
                    is_update_occured = True

                partial_bot_res: TextPacket = self.bot.receive()
                if partial_bot_res:
                    self.tts.feed(partial_bot_res)
                    is_update_occured = True

                _tts_out_packets = self.tts.receive()
                if _tts_out_packets:
                    self._output_buffer.put(
                        _tts_out_packets
                        # TODO note now that this is more than just partial voice bytes
                    )
                    is_update_occured = True

                if not is_update_occured:
                    # print('<agent>', end='', flush=True)
                    server.sleep(0.1)

        self._process = server.start_background_task(_start_looping_thread)

    def receive(self):
        return self._output_buffer.get_nowait()

    def reset_audio_buffers(self):
        """Resetting session and command audio logging buffers"""
        self.session_audio_buffer = AudioBuffer()

    def feed_audio_stream(self, audio_data):
        """Feed audio stream to STT """
        audio_packet = AudioPacket(audio_data)
        self.session_audio_buffer.put(audio_packet)
        self.stt.feed(audio_packet)

    def clean_up(self):
        """Clean up upon disconnection"""
        StorageManager.write_audio_file(self.session_audio_buffer.dump_to_packet())
        self.stt.reset_audio_stream()
        StorageManager.ensure_completion()