import io
import backoff
from pydub import AudioSegment
from gtts import gTTS, gTTSError
from .base import TTSEndpoint, audio_segment_to_audio_bytes_dict

class GTTSEndpoint(TTSEndpoint):
    def __init__(self, **kwargs):
        self.engine = gTTS

    def text_to_audio_file(self, text, filepath):
        tts = self.engine(text, lang='en')
        tts.save(filepath)

    def text_to_bytes(self, text):
        @backoff.on_exception(backoff.expo, gTTSError, max_tries=5)
        def get_audio_segment():
            for raw_audio_bytes in self.engine(text, lang='en', timeout=3).stream():
                yield AudioSegment.from_file(io.BytesIO(raw_audio_bytes), format="mp3")

        for audio_segment in get_audio_segment():
            yield audio_segment_to_audio_bytes_dict(audio_segment)