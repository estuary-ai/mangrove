import backoff
from typing import Dict, Generator
from pydub import AudioSegment
from abc import ABCMeta, abstractmethod
from loguru import logger


def get_mp3_audio_bytes(filepath='__temp__.mp3', chunk_size=1024) -> Generator[Dict, None, None]:
    import os
    import pydub
    # load mp3 file
    logger.debug(f"Loading mp3 file: {filepath}")
    @backoff.on_exception(backoff.expo, FileNotFoundError, max_tries=10)
    def load_mp3():
        return pydub.AudioSegment.from_mp3(filepath)
    audio = load_mp3()
    # delete the file
    os.remove(filepath)

    # chunk the audio
    for i in range(0, len(audio), chunk_size):
        yield {
            'audio_bytes': audio[i:i + chunk_size]._data,
            'frame_rate': audio.frame_rate,
            'sample_width': audio.sample_width,
            'channels': audio.channels
        }

def audio_segment_to_audio_bytes_dict(audio_segment: AudioSegment):
    return {
        'audio_bytes': audio_segment._data,
        'frame_rate': audio_segment.frame_rate,
        'sample_width': audio_segment.sample_width,
        'channels': audio_segment.channels
    }

class TTSEndpoint(metaclass=ABCMeta):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def text_to_audio_file(self, text, filepath):
        raise NotImplementedError()

    @abstractmethod
    def text_to_bytes(self, text) -> Generator[Dict, None, None]:
        raise NotImplementedError()

class Pyttsx3TTSEndpoint(TTSEndpoint):
    def __init__(self, voice_rate=100, voice_id=12, **kwargs):
        import pyttsx3
        self.engine = pyttsx3.init(debug=True)
        self.sample_width = 2
        self.channels = 1
        self.frame_rate = 22050
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
        def get_audio_segment():
            import io
            import scipy
            import numpy as np
            from pydub import AudioSegment
            wav_audio = np.array(self.engine.tts(text=text, speaker_wav="speaker.wav", language="en"))
            sample_rate = self.engine.synthesizer.output_sample_rate
            wav_norm = wav_audio * (32767 / max(0.01, np.max(np.abs(wav_audio))))
            wav_norm = wav_norm.astype(np.int16)
            wav_buffer = io.BytesIO()
            scipy.io.wavfile.write(wav_buffer, sample_rate, wav_norm)
            wav_buffer.seek(0)
            return AudioSegment.from_file(wav_buffer, format="wav")

        return audio_segment_to_audio_bytes_dict(get_audio_segment())

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
        def get_audio_bytes():
            return generate(text=text, voice=self.voice, model=self.model, stream=True)
        breakpoint()
        return {
            'audio_bytes': get_audio_bytes(),
            'frame_rate': 24000,
            'sample_width': 2,
            'channels': 1
        }

class GTTSEndpoint(TTSEndpoint):
    def __init__(self, **kwargs):
        from gtts import gTTS
        self.engine = gTTS

    def text_to_audio_file(self, text, filepath):
        tts = self.engine(text, lang='en')
        tts.save(filepath)

    def text_to_bytes(self, text):
        import backoff
        from gtts import gTTSError
        @backoff.on_exception(backoff.expo, gTTSError, max_tries=5)
        def get_audio_segment():
            import io
            from pydub import AudioSegment
            for raw_audio_bytes in self.engine(text, lang='en', timeout=3).stream():
                yield AudioSegment.from_file(io.BytesIO(raw_audio_bytes), format="mp3")

        for audio_segment in get_audio_segment():
            yield audio_segment_to_audio_bytes_dict(audio_segment)

    # def stream_bytes(self, text):
    #     tts = self.engine(text)
    #     for _bytes_chunk in tts.stream():
    #         yield _bytes_chunk