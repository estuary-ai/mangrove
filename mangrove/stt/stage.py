import torch
from typing import Optional, List
from queue import Empty as QueueEmpty


from core import TextPacket, AudioPacket
from core.stage import AudioToTextStage
from core.stage.base import SequenceMismatchException
from core.utils import Timer, logger
from .endpoints.faster_whisper import FasterWhisperEndpoint


class STTStage(AudioToTextStage):
    """Speech to Text Stage"""

    def __init__(
        self,
        frame_size=512 * 4,
        device=None,
        verbose=False,
    ):
        """Initialize STT Stage

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

        self._endpoint = FasterWhisperEndpoint(device=device)  # TODO make selection dynamic by name or type

        self._recorded_audio_length: int = 0  # FOR DEBUGGING
        self._interrupted_audio_packet: Optional[AudioPacket] = None

    def on_start(self):
        self._recorded_audio_length = 0  # FOR DEBUGGING
        self._interrupted_audio_packet = None

    def reset_audio_stream(self, reset_buffers=True) -> None:
        """Reset audio stream context"""
        if reset_buffers:
            self.log("[stt-hard-reset]", end="\n")
            self._endpoint.reset()
            self._input_buffer.reset()
            self._interrupted_audio_packet = None
        else:
            self.log("[stt-soft-reset]", end=" ")
        self._recorded_audio_length = 0

    def on_sleep(self):
        self.log('<stt>')

    def _process(self, audio_packet) -> Optional[TextPacket]:
        """Process audio buffer and return transcription if any found"""
        assert isinstance(audio_packet, AudioPacket), f"Expected AudioPacket, got {type(audio_packet)}"

        if len(audio_packet) < self.frame_size:
            raise Exception("Partial audio packet found; this should not happen")

        # Feed audio content to stream context
        logger.info(f"Processing {audio_packet}")
        if self._interrupted_audio_packet is not None:
            logger.debug("Interrupted audio packet found, appending at head")
            audio_packet = self._interrupted_audio_packet + audio_packet
            self._interrupted_audio_packet = None
        self._endpoint.feed(audio_packet)
        self._recorded_audio_length += audio_packet.duration # FOR DEBUGGING

        # Finish stream and return transcription if any found
        logger.debug("Trying to finish stream..")
        with Timer() as timer:
            transcription: Optional[str] = self._endpoint.get_transcription_if_any()
            if transcription:
                self.reset_audio_stream(reset_buffers=False)

                return TextPacket(
                    text=transcription,
                    partial=True,  # TODO is it?
                    start=False,
                    recog_time=timer.record(),
                    recorded_audio_length=self._recorded_audio_length,
                )

    def on_disconnect(self) -> None:
        self.reset_audio_stream()
        self.log("[disconnect]", end="\n")

    def on_interrupt(self):
        super().on_interrupt()
        # pack the data from endpoint to buffer
        self._interrupted_audio_packet = self._endpoint.get_buffered_audio_packet()
        while True:
            try:
                audio_packet = self._input_buffer.get_nowait()
                if self._interrupted_audio_packet is None:
                    self._interrupted_audio_packet = audio_packet
                else:
                    self._interrupted_audio_packet += audio_packet
            except QueueEmpty:
                break
        self.reset_audio_stream(reset_buffers=False)
        self.log("[interrupt]", end=" ")