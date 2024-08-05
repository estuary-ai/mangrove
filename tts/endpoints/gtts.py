import backoff
from typing import Generator
from pydub import AudioSegment
from gtts import gTTS, gTTSError
from core.data import AudioPacket
from core.utils import bytes_to_audio_packet
from .base import TTSEndpoint

class GTTSEndpoint(TTSEndpoint):
    def __init__(self, **kwargs):
        self.engine = gTTS

    def text_to_audio_file(self, text, filepath):
        tts = self.engine(text, lang='en')
        tts.save(filepath)

    def text_to_audio(self, text) -> Generator[AudioPacket, None, None]:
        @backoff.on_exception(backoff.expo, gTTSError, max_tries=5)
        def get_audio_packets():
            for raw_audio_bytes in self.engine(text, lang='en', timeout=3).stream():
                yield bytes_to_audio_packet(raw_audio_bytes, format="mp3")
        yield from get_audio_packets()