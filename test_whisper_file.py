import time
import torch
from transformers import pipeline
from transformers import WhisperForConditionalGeneration, WhisperProcessor


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device", device)

model = "tiny.en"

processor = WhisperProcessor.from_pretrained(f"openai/whisper-{model}")
model = WhisperForConditionalGeneration.from_pretrained(f"openai/whisper-{model}").to(
    device
)
model.to_bettertransformer()

transcriber = pipeline(
    "automatic-speech-recognition",
    model=model,
    feature_extractor=processor.feature_extractor,
    tokenizer=processor.tokenizer,
    chunk_length_s=30,
    device=device,
)

start_time = time.time()
transcription = transcriber("mlk.flac")
print("Took", time.time() - start_time, "seconds")

start_time = time.time()
transcription = transcriber("mlk.flac")
print("Took", time.time() - start_time, "seconds")


start_time = time.time()
transcription = transcriber("mlk.flac")
print("Took", time.time() - start_time, "seconds")

print("Transcription", transcription)

################################ TTS ###########################

from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan

processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")

model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts").to(device)
vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan").to(device)


from datasets import load_dataset

embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)


def synthesise(text):
    inputs = processor(text=text, return_tensors="pt")
    speech = model.generate_speech(
        inputs["input_ids"].to(device), speaker_embeddings.to(device), vocoder=vocoder
    )
    return speech.cpu()


start_time = time.time()
audio = synthesise(transcription["text"])
audio = synthesise(
    "A mix of English charm and Swedish melody, I'm your unique voice for multinational projects, bringing a cosmopolitan flair to your narratives."
)
print("Took", time.time() - start_time, "seconds")

start_time = time.time()
audio = synthesise(transcription["text"])
print("Took", time.time() - start_time, "seconds")

start_time = time.time()
audio = synthesise(transcription["text"])
print("Took", time.time() - start_time, "seconds")

start_time = time.time()
audio = synthesise(transcription["text"])
print("Took", time.time() - start_time, "seconds")
print("Audio", audio)
# breakpoint()
# torchaudio.save('mlk_tts.wav', audio, 16000)

from IPython.display import Audio

audio_play = Audio(audio, rate=16000)
with open("mlk_tts.wav", "wb") as f:
    f.write(audio_play.data)
