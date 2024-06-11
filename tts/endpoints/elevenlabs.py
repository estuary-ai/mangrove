import os
from elevenlabs import generate, save, set_api_key, voices
from .base import TTSEndpoint

class ElevenLabsTTSEndpoint(TTSEndpoint):
    def __init__(self, model='eleven_multilingual_v2', **kwargs):
        set_api_key(os.environ['ELEVENLABS_API_KEY'])
        self.voice = voices()[0]
        self.model = model

    def text_to_audio_file(self, text, filepath):
        save(self.text_to_bytes(text), filepath)

    def text_to_bytes(self, text):
        return generate(text=text, voice=self.voice, model=self.model)

    def stream_bytes(self, text):
        # def get_audio_bytes():
        #     return generate(text=text, voice=self.voice, model=self.model, stream=True)
        # breakpoint()
        # # TODO: implement stream_bytes
        # return {
        #     'audio_bytes': get_audio_bytes(),
        #     'frame_rate': 24000,
        #     'sample_width': 2,
        #     'channels': 1
        # }
        raise NotImplementedError("stream_bytes for ElevenLabsTTSEndpoint not implemented yet")