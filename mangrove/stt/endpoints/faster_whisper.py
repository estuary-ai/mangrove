from typing import Optional
from loguru import logger
from queue import Empty
from faster_whisper import WhisperModel

from core import AudioPacket
from core.utils import Timer
from .base import STTEndpoint

class FasterWhisperEndpoint(STTEndpoint):
    def __init__(self, model_name="distil-small.en", device=None):
        super().__init__()
        self.device = "auto" if device is None else device
        try:
            self.model = WhisperModel(model_name, device=self.device)
        except:
            logger.warning(f'Device {device} is not supported, defaulting to CPU!')
            self.model = WhisperModel(model_name, device='cpu')
        self.reset()

    def get_transcription_if_any(self) -> Optional[str]:
        """Get transcription if available

        Returns:
            str: Transcription if available, else None
        """

        logger.trace("Waiting for transcription ... ")

        audio_packet = self.get_buffered_audio_packet()
        if audio_packet is None:
            return None
        
        
        with Timer() as timer:
            segments, _ = self.model.transcribe(
                audio_packet.float,
                language='en',
                vad_filter=True,
                without_timestamps=True
            )
            _out = list(segments)
            if len(_out) >= 1:
                _out = " ".join([segment.text for segment in _out])
            logger.success(f"Took {timer.record()} seconds")

        # if _out:
        #     logger.success(f"Transcription: {_out}")
        #     # Save the transcription to a wav file
        #     filepath = f"blackbox/transcribed_{audio_packet.timestamp}.wav"
        #     audio_packet.to_wav(filepath)

        return _out

    def reset(self):
        while True:
            try:
                self.input_queue.get_nowait()
            except Empty:
                break
        logger.debug(f"Resetting {self.__class__.__name__} endpoint")
