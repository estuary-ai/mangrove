from abc import ABC, abstractmethod
from loguru import logger

class TTSEndpoint(ABC):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def text_to_audio_file(self, text, filepath):
        raise NotImplementedError()

    @abstractmethod
    def text_to_bytes(self, text):
        raise NotImplementedError()

class Pyttsx3TTSEndpoint(TTSEndpoint):
    def __init__(self, voice_rate=100, voice_id=12, **kwargs):
        import pyttsx3
        self.engine = pyttsx3.init(debug=True)

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

    def text_to_bytes(self, text):
        self.text_to_audio_file(text, '__temp__.mp3')
        import backoff
        @backoff.on_exception(backoff.expo, FileNotFoundError, max_tries=10)
        def get_audio_bytes():
            import os
            audio_bytes = open('__temp__.mp3', 'rb').read()
            # delete the file
            os.remove('__temp__.mp3')
            return audio_bytes
        return get_audio_bytes()



class TTSLibraryEndpoint(TTSEndpoint):
    def __init__(self,  device=None, **kwargs):
        import torch
        from TTS.api import TTS
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.engine = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        self._ensure_speaker_wav()

    def _ensure_speaker_wav(self):
        import os
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
        # return self.engine.tts(text)
        self.text_to_audio_file(text, '__temp__.wav')
        import backoff
        @backoff.on_exception(backoff.expo, FileNotFoundError, max_tries=10)
        def get_audio_bytes():
            import os
            audio_bytes = open('__temp__.wav', 'rb').read()
            # delete the file
            os.remove('__temp__.wav')
            return audio_bytes
        return get_audio_bytes()


class ElevenLabsTTSEndpoint(TTSEndpoint):
    def __init__(self, model='eleven_multilingual_v2', **kwargs):
        import os
        from elevenlabs import set_api_key
        set_api_key(os.environ['ELEVENLABS_API_KEY'])

        from elevenlabs import voices
        self.voice = voices()[0]
        self.model = model

    def text_to_audio_file(self, text, filepath):
        from elevenlabs import save
        save(self.text_to_bytes(text), filepath)

    def text_to_bytes(self, text):
        from elevenlabs import generate
        return generate(text=text, voice=self.voice, model=self.model)

    def stream_bytes(self, text):
        from elevenlabs import generate
        return generate(text=text, voice=self.voice, model=self.model, stream=True)

class GTTSEndpoint(TTSEndpoint):
    def __init__(self, **kwargs):
        from gtts import gTTS
        self.engine = gTTS

    def text_to_audio_file(self, text, filepath):
        tts = self.engine(text)
        tts.save(filepath)

    def text_to_bytes(self, text):
        # self.text_to_audio_file(text, '__temp__.mp3')
        # import backoff
        # @backoff.on_exception(backoff.expo, FileNotFoundError, max_tries=10)
        # def get_audio_bytes():
        #     import os
        #     audio_bytes = open('__temp__.mp3', 'rb').read()
        #     # delete the file
        #     os.remove('__temp__.mp3')
        #     return audio_bytes
        # return get_audio_bytes()

        import backoff
        from gtts import gTTSError
        @backoff.on_exception(backoff.expo, gTTSError, max_tries=5)
        def get_audio_bytes():
            return b''.join(self.engine(text, timeout=3).stream())
        return get_audio_bytes()

    def stream_bytes(self, text):
        tts = self.engine(text)
        for _bytes_chunk in tts.stream():
            yield _bytes_chunk