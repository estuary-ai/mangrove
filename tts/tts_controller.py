import os
import time
import pyttsx3
from TTS.api import TTS
import inflect
import math
from decimal import Decimal
from storage_manager import write_output

class TTSController:

    def __init__(self, engine='pyttsx3', voice_rate=190, voice_id=1, storage_path='res-speech'):
        # ENGINE INIT START
        # TODO reinitialize engine
        self.engine_type = engine
        breakpoint()
        if engine == "pyttsx3":
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', voice_rate)
            voices = self.engine.getProperty('voices')
            # voice_str = "\n".join(voices)
            # write_output(f'Available Voices:\n {voice_str}')
            # write_output(f'Chosen: {voices[voice_id].id}')
            self.engine.setProperty('voice', voices[voice_id].id)
        elif engine == "tts":
            self.engine = TTS(TTS.list_models()[0])
        # ENGINE INIT END
        
        self.storage_path = storage_path
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)
        self.recent_created_audio_files = []
        self.number_to_word_converter = inflect.engine()

    def _create_audio_files(self, texts):
        if not isinstance(texts, list):
            texts = [texts]
        generation_id = str(int(time.time()))
        self.recent_created_audio_files = []
        for id, text in enumerate(texts):
            filepath = f'{self.storage_path}/{generation_id}_audio_{id}.wav'
            # TODO START
            if self.engine_type == "pyttsx3":
                self.engine.save_to_file(text, filepath)
                self.engine.runAndWait()
            elif self.engine_type == "tts":
                self.engine.tts_to_file(text=text, speaker=self.engine.speakers[0], language=self.engine.languages[0], file_path=filepath)
            # TODO END
            self.recent_created_audio_files.append(filepath)
        return self.recent_created_audio_files
    

    
    def _get_audio_bytes_stream(self, texts=None):
        if not isinstance(texts, list):
            texts = [texts]
        if texts is not None:
            self._create_audio_files(texts)
        audio_files_bytes = b''
        for audio_file in self.recent_created_audio_files:
            with open(audio_file, 'rb') as f:
                audio_files_bytes += f.read()
        return audio_files_bytes

    def delete_audio_files(self):
        for audio_file in self.recent_created_audio_files:
            os.remove(audio_file)
        self.recent_created_audio_files = []

    def get_feature_read_bytes(self, feature, values, units=None):
        
        text = feature + " is equal to "
        if units is None:
            units = ["" for _ in values]

        for value, unit in zip(values, units):
            text += self._textify_number(round(Decimal(value), 2)) + " " + unit

        return self._get_audio_bytes_stream(text)
    
    def get_plain_text_read_bytes(self, text):
        return self._get_audio_bytes_stream(text)
    
    def _textify_number(self, num):
        return self.number_to_word_converter.number_to_words(num)
    