import os
import time
import pyttsx3
import inflect
import math
from decimal import Decimal


class TTSController:

    def __init__(self, voice_rate=140, voice_id=1, storage_path='res-speech'):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', voice_rate)
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[voice_id].id)
        self.storage_path = storage_path
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)
        self.recent_created_audio_files = []

        self.number_to_word_converter = inflect.engine()

    def create_audio_files(self, texts):
        if not isinstance(texts, list):
            texts = [texts]
        generation_id = str(int(time.time()))
        self.recent_created_audio_files = []
        for id, text in enumerate(texts):
            filepath = f'{self.storage_path}/{generation_id}_audio_{id}.wav'
            self.engine.save_to_file(text, filepath)
            self.engine.runAndWait()
            self.recent_created_audio_files.append(filepath)
        return self.recent_created_audio_files

    def get_audio_bytes_stream(self, texts=None):
        if not isinstance(texts, list):
            texts = [texts]
        if texts is not None:
            self.create_audio_files(texts)
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
            text += self.textify_number(round(Decimal(value), 2)) + " " + unit

        return self.get_audio_bytes_stream(text)

    def textify_number(self, num):
        return self.number_to_word_converter.number_to_words(num)