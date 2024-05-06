import io
import os
import scipy
import torch
import numpy as np
from pydub import AudioSegment
from TTS.api import TTS
from loguru import logger
from .base import TTSEndpoint, audio_segment_to_audio_bytes_dict
from tts.endpoints.elevenlabs import ElevenLabsTTSEndpoint

class TTSLibraryEndpoint(TTSEndpoint):
    def __init__(self,  device=None, **kwargs):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.engine = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        self._ensure_speaker_wav()

    def _ensure_speaker_wav(self):
        if not os.path.exists('speaker.wav'):
            # generate speaker.wav using ElevenLabsTTSEndpoint
            logger.warning("Generating speaker.wav using ElevenLabsTTSEndpoint as it is not available.")
            ElevenLabsTTSEndpoint().text_to_audio_file(
                "Hello, I am your assistant. I am here to help you with your tasks."
                "I am a digital assistant created by the Estuary team. I am here to help you with your tasks.",
                'speaker.wav'
            )

    def text_to_audio_file(self, text, filepath):
        self.engine.tts_to_file(text=text, file_path=filepath, speaker_wav="speaker.wav", language="en")

    def text_to_bytes(self, text):
        def get_audio_segment():
            wav_audio = np.array(self.engine.tts(text=text, speaker_wav="speaker.wav", language="en"))
            sample_rate = self.engine.synthesizer.output_sample_rate
            wav_norm = wav_audio * (32767 / max(0.01, np.max(np.abs(wav_audio))))
            wav_norm = wav_norm.astype(np.int16)
            wav_buffer = io.BytesIO()
            scipy.io.wavfile.write(wav_buffer, sample_rate, wav_norm)
            wav_buffer.seek(0)
            return AudioSegment.from_file(wav_buffer, format="wav")

        return audio_segment_to_audio_bytes_dict(get_audio_segment())