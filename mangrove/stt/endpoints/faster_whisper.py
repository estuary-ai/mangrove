from typing import Optional
from queue import Empty
from faster_whisper import WhisperModel

from core.utils import logger
from core import AudioPacket
from core.utils import Timer
from .base import STTEndpoint

class FasterWhisperEndpoint(STTEndpoint):
    def __init__(self, model_name="distil-medium.en", device=None):
        super().__init__()
        self.device = "auto" if device is None else device
        try:
            self.model = WhisperModel(model_name, device=self.device, compute_type="int8")
        except:
            logger.warning(f'Device {device} is not supported, defaulting to CPU!')
            self.model = WhisperModel(model_name, device='cpu')
        
        # Custom VAD parameters
        self.vad_parameters = {
            "threshold": 0.3,          # Lower = more sensitive to quiet speech
            "min_speech_duration_ms": 500,    # Minimum speech chunk
            "min_silence_duration_ms": 1000,  # Longer pause needed to split
            "speech_pad_ms": 600,            # Padding around speech segments
        }
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
                vad_parameters=self.vad_parameters,  # Pass custom VAD settings
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

        if isinstance(_out, list):
            assert len(_out) == 0, "Transcription list is empty"
            return None

        assert isinstance(_out, str), f"Transcription must be a string, got {type(_out)}"
        return _out

    def reset(self):
        while True:
            try:
                self.input_queue.get_nowait()
            except Empty:
                break
        logger.debug(f"Resetting {self.__class__.__name__} endpoint")
