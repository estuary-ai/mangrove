import torch
from typing import Optional
from loguru import logger

from core import TextPacket
from core.data import DataPacket
from queue import Empty as QueueEmpty
from core.stage import AudioToTextStage
from core.utils import Timer
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
            frame_size (int, optional): audio frame size. Defaults to 320.
            device (str, optional): Device to use. Defaults to None.
            verbose (bool, optional): Whether to print debug messages. Defaults to False.

        Raises:
            ValueError: If custom scorer is defined but not found
        """
        super().__init__(frame_size=frame_size, verbose=verbose)

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.endpoint = FasterWhisperEndpoint(device=device) # TODO make selection dynamic by name or type

    def on_start(self):
        self.recorded_audio_length = 0 # FOR DEBUGGING

    def on_sleep(self):
        self.log('<stt>')


    def _process(self, audio_packet) -> Optional[TextPacket]:
        """Process audio buffer and return transcription if any found"""
        if audio_packet is None:
            return

        if len(audio_packet) < self.frame_size:
            raise Exception("Partial audio packet found; this should not happen")

        # Feed audio content to stream context
        logger.info(f"Processing {audio_packet}")
        self.endpoint.feed(audio_packet)
        self.recorded_audio_length += audio_packet.duration # FOR DEBUGGING

        # Finish stream and return transcription if any found
        logger.debug("Trying to finish stream..")
        with Timer() as timer:
            transcription: Optional[str] = self.endpoint.get_transcription_if_any()
            if transcription:
                self.reset_audio_stream(reset_buffers=False)

                return TextPacket(
                    text=transcription,
                    partial=True, # TODO is it?
                    start=False,
                    recog_time=timer.record(),
                    recorded_audio_length=self.recorded_audio_length,
                )
    
    def reset_audio_stream(self, reset_buffers=True) -> None:
        """Reset audio stream context"""
        if reset_buffers:
            self.log("[stt-hard-reset]", end="\n")
            self.endpoint.reset()
            self._input_buffer.reset()
        else:
            self.log("[stt-soft-reset]", end=" ")
        self.recorded_audio_length = 0

    def on_disconnect(self) -> None:
        self.reset_audio_stream()
        self.log("[disconnect]", end="\n")