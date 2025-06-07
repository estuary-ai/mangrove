import warnings
from mangrove import (
    VADStage,
    STTStage,
    BotStage,
    TTSStage,
)
from storage_manager import StorageManager
from core import AudioBuffer
from core.stage import PipelineSequence
from core.utils import logger

# TODO check on this later
warnings.filterwarnings("ignore", category=UserWarning)

class BasicConversationalAgent(PipelineSequence):
    """Agent controller for the conversational AI server."""

    def __init__(
        self,
        device=None,
        bot_endpoint="openai",
        tts_endpoint="gtts",
        welcome_msg: str="Welcome, AI server connection is succesful.",
        verbose=False,
    ):
        super().__init__(verbose=verbose)

        vad = VADStage(device=device)
        stt = STTStage(device=device)
        bot = BotStage(endpoint=bot_endpoint)
        tts = TTSStage(endpoint=tts_endpoint)
        self.startup_audiopacket = None
        if welcome_msg:
            self.startup_audiopacket = tts.read(
                welcome_msg,
                as_generator=False
            )

        self.add_stage(vad)
        self.add_stage(stt)
        self.add_stage(bot)
        self.add_stage(tts)

    def on_start(self):
        super().on_start()
        self.session_audio_buffer = AudioBuffer()

    def on_connect(self):
        logger.info("Connected to the server.")
        if self.startup_audiopacket:
            from copy import deepcopy
            self._host.emit_bot_voice(deepcopy(self.startup_audiopacket))
        logger.info("Ready to receive audio packets.")

    def on_disconnect(self):
        """Clean up upon disconnection"""
        logger.info("Disconnected from the server.")
        if self.session_audio_buffer.is_empty():
            return
        StorageManager.write_audio_file(self.session_audio_buffer.dump_to_packet())
        StorageManager.ensure_completion()
        logger.info("Session completed.")