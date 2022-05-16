import os
import pyttsx3

class TTSController:

    def __init__(self):

        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 120)
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[1].id)

    def create_audio_files(self, texts):

        self.audio_files = []

        for id, text in enumerate(texts):
            self.engine.save_to_file(text, f'audio_{id}.wav')
            self.engine.runAndWait()
            self.audio_files.append(f'audio_{id}.wav')

        return self.audio_files

    def delete_audio_files(self):

        for audio_file in self.audio_files:
            os.remove(audio_file)