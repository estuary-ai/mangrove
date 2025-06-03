from TTS.api import TTS

if __name__ == "__main__":
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
    for i in range(10):
        output_file_name = f"skeleton_feet{i}.wav"
        tts.tts_to_file(text="got myself some fancy skeleton feet, ain't that right?",
                        file_path=output_file_name,
                        speaker_wav="speaker.wav",
                        language="en")