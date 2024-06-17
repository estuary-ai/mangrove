from loguru import logger
from typing import Optional
from queue import Empty
from storage_manager import StorageManager
from stt import STTController
from bot import BotController
from tts import TTSController
from core import TextPacket, AudioPacket, AudioBuffer
from core.data.data_packet import DataPacket
from core.stage import PipelineStage


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from server import DigitalAssistant

import warnings
# TODO check on this later
warnings.filterwarnings("ignore", category=UserWarning)

class AssistantController(PipelineStage):
    """Main controller for the assistant."""

    def __init__(
        self,
        verbose=True,
        device=None,
        tts_endpoint="gtts",
        welcome_msg: str="Welcome, AI server connection is succesful.",
    ):
        """Initialize the assistant controller."""
        super().__init__(verbose=False) # TODO

        self.stt = STTController(device=device)
        self.bot = BotController()
        self.tts = TTSController(tts_endpoint)

        self.welcome_msg = welcome_msg
        self.startup_audiopacket: AudioPacket = None
        self.started = False


    def on_connect(self, host):
        if self.startup_audiopacket:
            from copy import deepcopy
            host.emit_bot_voice(deepcopy(self.startup_audiopacket))

    def on_disconnect(self):
        """Clean up upon disconnection"""
        if self.session_audio_buffer.is_empty():
            return

        StorageManager.write_audio_file(self.session_audio_buffer.dump_to_packet())
        StorageManager.ensure_completion()

    def on_sleep(self):
        self.log("<assistant>")

    def on_start(self):
        if self.started:
            raise Exception("Assistant already started")

        self.session_audio_buffer = AudioBuffer()

        def _on_ready_callback(
            stage: PipelineStage,
            next_stage: Optional[PipelineStage],
            data_packet: DataPacket
        ):
            if next_stage is not None:
                if not isinstance(data_packet, next_stage.input_type):
                    raise ValueError(f"Data packet type mismatch, expected {next_stage.input_type}, got {type(data_packet)}")

                logger.debug(f"Feeding {data_packet} from {stage} to {next_stage}")
                next_stage.feed(data_packet)

            if isinstance(stage, STTController):
                self.server.emit_stt_response(data_packet)
            elif isinstance(stage, BotController):
                self.server.emit_bot_response(data_packet)
            elif isinstance(stage, TTSController):
                self.server.emit_bot_voice(data_packet)
            else:
                raise ValueError("Unknown Pipeline Stage Type")


        self.stt.on_ready_callback = lambda p: _on_ready_callback(self.stt, self.bot, p)
        self.stt.start(server=self.server)
        self.bot.on_ready_callback = lambda p: _on_ready_callback(self.bot, self.tts, p)
        self.bot.start(server=self.server)
        self.tts.on_ready_callback = lambda p: _on_ready_callback(self.tts, None, p)
        self.tts.start(server=self.server)

        if self.welcome_msg:
            self.startup_audiopacket = self.tts.read(
                self.welcome_msg,
                as_generator=False
            )

        self.started = True

    def _unpack(self):
        try:
            return self._input_buffer.get_nowait()
        except Empty:
            return None

    def _process(self, data_packet: DataPacket): # TODO temporarily assuming AudioPacket
        if data_packet is None:
            return None
        if not isinstance(data_packet, self.stt.input_type):
            raise ValueError(f"Data packet type mismatch, expected {self.stt.input_type}, got {type(data_packet)}")
        self.stt.feed(data_packet)
