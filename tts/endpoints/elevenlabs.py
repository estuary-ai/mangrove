import os
from elevenlabs.client import ElevenLabs
from .base import TTSEndpoint

class ElevenLabsTTSEndpoint(TTSEndpoint):
    def __init__(self, model_name='eleven_multilingual_v2', **kwargs):
        self.client = ElevenLabs(api_key=os.environ['ELEVENLABS_API_KEY'])
        self.model_name = model_name

    def text_to_audio_file(self, text, filepath):
        _bytes = self.text_to_bytes(text)
        with open(filepath, 'wb') as f:
            for chunk in _bytes:
                f.write(chunk)

    def text_to_bytes(self, text):
        return self.client.generate(text=text, model=self.model_name)

    def stream_bytes(self, text):
        return self.client.generate(text=text, model=self.model_name, stream=True)