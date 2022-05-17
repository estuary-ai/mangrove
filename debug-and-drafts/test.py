# -*- coding: utf-8 -*-
import sys
sys.path.insert(1, '../')
import numpy as np
import sounddevice as sd
from STTController import STTController

stt = STTController(
                 model_path='../models/ds-model/deepspeech-0.9.3-models')

f = open("sample_audio_binary.txt", mode='rb')
audio = f.read()
print("total length in bytes:", len(audio))

sd.play(np.frombuffer(audio, dtype=np.int16), 16000)

stt.create_stream()

frame_size = 2048//2//3 + 1
print('Frame Size', frame_size)
text = ""
for i in range(0, len(audio), frame_size):
    chunk = audio[i:i+frame_size]
    if len(chunk) < frame_size:
        break
    result = stt.process_audio_stream(chunk)
    if result is not None:
        print("result", result)

print("leftover chunks", len(chunk))
print('total debug', stt.debug_total)
print('voice debug', stt.debug_voice)
print('silence debug', stt.debug_silence)
sd.wait()