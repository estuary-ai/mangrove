import os
import numpy as np
from typing import Generator
from elevenlabs.client import ElevenLabs
from core.data import AudioPacket, TextPacket
from core.utils.audio import bytes_to_audio_packet
from .base import TTSEndpoint

class ElevenLabsTTSEndpoint(TTSEndpoint):
    def __init__(self, model_name='eleven_multilingual_v2', **kwargs):
        self.client = ElevenLabs(api_key=os.environ['ELEVENLABS_API_KEY'])
        self.model_name = model_name

    def text_to_audio_file(self, text, filepath) -> None:
        _audio_packets = self.text_to_audio(TextPacket(text=text, partial=False, start=True))
        with open(filepath, 'wb') as f:
            for chunk in _audio_packets:
                f.write(chunk)

    def text_to_audio(self, text_packet: TextPacket) -> Generator[AudioPacket, None, None]:
        # TODO fix stuttering output
        leftover = None
        for chunk in self.client.generate(
            text=text_packet.text, model=self.model_name, 
            output_format="mp3_22050_32",
            stream=True
        ):
            if leftover is not None:
                chunk = leftover + chunk
                leftover = None
            try:
                yield bytes_to_audio_packet(chunk, format="mp3")
            except Exception as e:
                leftover = chunk
                continue