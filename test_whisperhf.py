import os
import sys
import torch
import openai
import sounddevice
from transformers.pipelines.audio_utils import ffmpeg_microphone_live
from transformers import pipeline
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset

device = "cuda:0" if torch.cuda.is_available() else "cpu"


classifier = pipeline(
    "audio-classification", model="MIT/ast-finetuned-speech-commands-v2", device=device
)


def launch_fn(
    wake_word="marvin",
    prob_threshold=0.5,
    chunk_length_s=2.0,
    stream_chunk_s=0.25,
    debug=False,
):
    print("Possible Wake Words", classifier.model.config.label2id.keys())
    print("Wake Word:", wake_word)
    if wake_word not in classifier.model.config.label2id.keys():
        raise ValueError(
            f"Wake word {wake_word} not in set of valid class labels, pick a wake word in the set {classifier.model.config.label2id.keys()}."
        )

    sampling_rate = classifier.feature_extractor.sampling_rate

    mic = ffmpeg_microphone_live(
        sampling_rate=sampling_rate,
        chunk_length_s=chunk_length_s,
        stream_chunk_s=stream_chunk_s,
    )

    print("Listening for wake word...")
    for prediction in classifier(mic):
        prediction = prediction[0]
        if debug:
            print(prediction)
        if prediction["label"] == wake_word:
            if prediction["score"] > prob_threshold:
                return True


transcriber = pipeline(
    "automatic-speech-recognition", model="openai/whisper-base.en", device=device
)


from transformers import pipeline
from transformers import WhisperForConditionalGeneration, WhisperProcessor

model = "base.en"
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


def transcribe(chunk_length_s=5.0, stream_chunk_s=1.0):
    sampling_rate = transcriber.feature_extractor.sampling_rate

    mic = ffmpeg_microphone_live(
        sampling_rate=sampling_rate,
        chunk_length_s=chunk_length_s,
        stream_chunk_s=stream_chunk_s,
    )
    print("Start speaking...")
    for item in transcriber(mic, generate_kwargs={"max_new_tokens": 128}):
        sys.stdout.write("\033[K")
        print(item["text"], end="\r")
        if not item["partial"][0]:
            break

    return item["text"]


openai.api_key = os.environ["OPENAI_API_KEY"]


def query(text):
    print(f"Querying...: {text}")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that can make interesting conversations.",
            },
            {"role": "user", "content": text},
        ],
    )

    return response["choices"][0]["message"]["content"]


# processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
# model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts").to(device)
# vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan").to(device)
# embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
# speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)

# def synthesise(text):
#     inputs = processor(text=text, return_tensors="pt")
#     speech = model.generate_speech(
#         inputs["input_ids"].to(device), speaker_embeddings.to(device), vocoder=vocoder
#     )
#     return speech.cpu()

# pipe = pipeline("text-to-speech", model="suno/bark-small", device=device)

# def synthesise(text):
#     return pipe(text)


from fairseq.checkpoint_utils import load_model_ensemble_and_task_from_hf_hub
from fairseq.models.text_to_speech.hub_interface import TTSHubInterface
import IPython.display as ipd


models, cfg, task = load_model_ensemble_and_task_from_hf_hub(
    "facebook/fastspeech2-en-ljspeech",
    arg_overrides={"vocoder": "hifigan", "fp16": True, "device": device},
)
model = models[0]
model.to(device)
TTSHubInterface.update_cfg_with_data_cfg(cfg, task.data_cfg)
generator = task.build_generator([model], cfg)


def synthesise(text):
    sample = TTSHubInterface.get_model_input(task, text)
    for k, v in sample.items():
        if isinstance(v, dict):
            for k_i, v_i in v.items():
                if torch.is_tensor(v_i):
                    sample[k][k_i] = v_i.to(device)
    wav, rate = TTSHubInterface.get_prediction(task, model, generator, sample)
    return {"audio": wav.cpu(), "sampling_rate": rate}


text = "Hello, this is a test run."
tts = synthesise(text)
sounddevice.play(tts["audio"].squeeze(), tts["sampling_rate"], blocking=True)

################ MAIN LOOP ################
print("Welcome to Testing Agent!")
print('Say "marvin" to activate')
print('Say "goodbye" to exit')

while True:
    print("Waiting for wake word...")
    launch_fn()
    transcription = transcribe()
    print(f"Transcription: {transcription}\n")
    response = query(transcription)
    print(f"Response: {response}\n")
    tts = synthesise(response)
    print(f"Audio: playing..\n")
    sounddevice.play(tts["audio"].squeeze(), tts["sampling_rate"], blocking=True)

    if transcription == "goodbye":
        break
