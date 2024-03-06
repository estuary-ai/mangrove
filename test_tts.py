from tts import TTSController


# import pyttsx3
# engine = pyttsx3.init()
# voices = engine.getProperty('voices')
# for i, voice in enumerate(voices):
#     print(i)
#     print(voice, voice.id)
#     engine.setProperty('voice', voice.id)
#     engine.say("Hello World!")
#     engine.runAndWait()
#     engine.stop()

text_sample = "Thank you for asking! As an AI, I don't have feelings, but I'm here and ready to assist you. How can I help you today?"
tts_controller = TTSController(endpoint="pyttsx3", endpoint_kwargs={"voice_rate": 150, "voice_id": 14})
# tts_controller = TTSController(endpoint="elevenlabs")
print('Creating audio file')
tts_controller.get_plain_text_read_bytes(text_sample)
print('Creating audio file')
tts_controller.get_plain_text_read_bytes(text_sample)
print('Creating audio file')
# tts_controller = TTSController(endpoint="elevenlabs")
tts_controller.get_plain_text_read_bytes(text_sample)
print('TTS Controller created audio file')
# play audio file
import numpy as np
from playsound import playsound
playsound(tts_controller.created_audio_files[0])

