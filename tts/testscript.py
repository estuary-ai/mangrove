from TTS.api import TTS

# List available 🐸TTS models and choose the first one
model_name = TTS.list_models()[0]
# Init TTS
engine = TTS(model_name)
# Run TTS
# ❗ Since this model is multi-speaker and multi-lingual, we must set the target speaker and the language
# Text to speech with a numpy output
wav = engine.tts("Your current oxygen level is fifty percent.", speaker=engine.speakers[0], language=engine.languages[0])
breakpoint()
# Text to speech to a file
engine.tts_to_file(text="Your current oxygen level is fifty percent. Open the navigation menu.", speaker=engine.speakers[0], language=engine.languages[0], file_path="output.wav")