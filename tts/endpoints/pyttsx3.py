from typing import Dict, Generator
from .base import TTSEndpoint, get_mp3_audio_bytes

class Pyttsx3TTSEndpoint(TTSEndpoint):
    def __init__(self, voice_rate=100, voice_id=12, **kwargs):
        # MAKE IT SINGLETON AS PYTTSX3 DOESN'T SUPPORT MULTIPLE INSTANCES
        import pyttsx3
        self.engine = pyttsx3.init(debug=True)
        # self.sample_width = 2
        # self.channels = 1
        # self.frame_rate = 22050
        self.engine.setProperty("rate", voice_rate)
        voices = self.engine.getProperty("voices")
        # voice_str = "\n".join(voices)
        # write_output(f'Available Voices:\n {voice_str}')
        # write_output(f'Chosen: {voices[voice_id].id}')
        self.engine.setProperty("voice", voices[voice_id].id)
        self.engine.startLoop(False)

    def text_to_audio_file(self, text, filepath):
        self.engine.save_to_file(text, filepath)
        # try:
        #     self.engine.startLoop(False)
        # except:
        #     pass
        self.engine.iterate()
        # self.engine.runAndWait()

    def text_to_bytes(self, text) -> Generator[Dict, None, None]:
        self.text_to_audio_file(text, '__temp__.mp3')
        for audio_bytes_dict in get_mp3_audio_bytes(filepath='__temp__.mp3', chunk_size=1024):
            yield audio_bytes_dict
