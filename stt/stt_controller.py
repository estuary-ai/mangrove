import time
import torch
from typing import Optional
from loguru import logger
from core import AudioPacket, TextPacket, AudioBuffer
from core.stage import AudioToTextStage
from .vad.silero import SileroVAD
from .endpoints.faster_whisper import FasterWhisperEndpoint

class STTController(AudioToTextStage):
    """Speech to Text Controller"""

    def __init__(
        self,
        frame_size=512 * 4,
        device=None,
        verbose=False,
    ):
        """Initialize STT Controller

        Args:
            sample_rate (int, optional): Sample rate. Defaults to 16000.
            silence_threshold (int, optional): Silence threshold. Defaults to 200 ms.
            frame_size (int, optional): audio frame size. Defaults to 320.
            device (str, optional): Device to use. Defaults to None.
            verbose (bool, optional): Whether to print debug messages. Defaults to False.

        Raises:
            ValueError: If custom scorer is defined but not found
        """
        super().__init__(frame_size=frame_size, verbose=verbose)

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = FasterWhisperEndpoint(device=device) # TODO make selection dynamic by name or type

        self.debug_total_size = 0
        self._command_audio_buffer = AudioBuffer(frame_size=frame_size)

    def on_start(self):
        self._create_stream()

    def on_sleep(self):
        self.log('<stt>')

    def _create_stream(self) -> None:
        """Create a new stream context"""
        self.model.reset()

        ##### DEBUG #####
        self.recorded_audio_length = 0
        logger.warning("Reset debug feed frames")

    # TODO clean
    # def feed(self, audio_packet: AudioPacket):
    #     """Feed audio packet to STT Controller

    #     Args:
    #         audio_packet (AudioPacket): Audio packet to feed
    #     """
    #     # if self._command_audio_buffer.is_empty():
    #     #     self._create_stream()
    #     #     self.log("receiving first stream of audio command")
    #     self._input_buffer.put(audio_packet)``

    def _process(self, audio_packet) -> Optional[TextPacket]:
        """Process audio buffer and return transcription if any found"""

        if audio_packet is None:
            return

        if len(audio_packet) < self.frame_size:
            # partial TODO maybe add to buffer
            logger.error(f"Partial audio packet found: {len(audio_packet)}")
            raise Exception("Partial audio packet found")

        self.debug_total_size += len(audio_packet) # For DEBUGGING

        # Feed audio content to stream context
        self.model.feed(audio_packet)

        ##### DEBUG #####
        self.recorded_audio_length += audio_packet.duration


        # Finish stream and return transcription if any found
        logger.debug("Trying to finish stream..")
        time_start_recog = round(time.time() * 1000)

        # if force_clear_buffer:
        #     # TODO look into this
        #     # feed all remaining audio packets to stream context
        #     self._process(self._unpack())

        transcription = self.model.get_transcription()
        if transcription:
            logger.success(f"Recognized Text: {transcription}")
            recog_time = round(time.time() * 1000) - time_start_recog
            self.refresh()
            self._create_stream() # TODO this was just moved here, verify

            return TextPacket(
                text=transcription,
                partial=False, # TODO is it?
                start=True,
                recog_time=recog_time,
                recorded_audio_length=self.recorded_audio_length,
            )
    
        

    def reset_audio_stream(self) -> None:
        """Reset audio stream context"""
        self.log("[reset]", end="\n")
        if not self._command_audio_buffer.is_empty():
            from storage_manager import StorageManager
            StorageManager.play_audio_packet(self._command_audio_buffer)

        self._create_stream()
        self._input_buffer.reset()
        self._command_audio_buffer.reset()
        self.model.reset()

    # TODO use after some detection
    def refresh(self) -> None:
        """Refresh STT Controller"""
        self.log('[refresh]', end='\n')
        # self.reset_audio_stream()

    def on_disconnect(self) -> None:
        self.reset_audio_stream()
        self.log("[disconnect]", end="\n")