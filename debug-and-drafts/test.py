# -*- coding: utf-8 -*-
import sys
sys.path.insert(1, '../')
import numpy as np
import sounddevice as sd

from stt import STTController
from bot import BotController
from tts import TTSController

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import tensorflow as tf
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)


print("Initializing STT Controller")
stt = STTController(model_path='../models/ds-model/deepspeech-0.9.3-models', verbose=True)
stt.set_regular_focus()

# print("Initializing Bot Controller")
# bot = BotController(
#                 model_path='../models/rasa-model/20220523-140335.tar.gz'
#                 )
# print("Initializing TTS Controller")
# tts = TTSController()    
# print("Server is about to be Up and Running..")

from os import walk
samples_path = '../sample-audio-binary'


while(True):
    filenames = next(walk(samples_path), (None, None, []))[2]  # [] if no file
    for i, filename in enumerate(filenames):
        print(f'{i+1}. {filename}')
    filenumber = input("Enter 0 for exit or file-number:")
    if int(filenumber) == 0:
        print("Terminating")
        break 
    filename = filenames[int(filenumber)-1]
    print("filename:", filename)
    f = open(f'{samples_path}/{filename}', mode='rb')
    audio = f.read()
    # audio = audio[len(audio)//4:]
    
    print("total length in bytes:", len(audio))
    print("playing audio..")
    sd.play(np.frombuffer(audio, dtype=np.int16), 16000)
    sd.wait()

    stt.create_stream()
    # stt._feed_audio_content(audio)
    # stt_res = stt._finish_stream()
    stt_res = stt.process_audio_stream(audio)

    print('audiobuffer: ', len(stt.buffered_data))
    print('audiofeed debug', stt.debug_feed)
    print('total debug', stt.debug_total)
    print('voice debug', stt.debug_voice)
    print('silence debug', stt.debug_silence)
    print('debug_silence_state', stt.debug_silence_state)

    print('User: ' + str(stt_res))
    # print('silence_start', stt.debug_silence_state)
    # bot_res = bot.send_user_message(stt_res['text'])
    # print('SENVA: ' + str(bot_res))    
    # if bot_res.get('text'):
    #     bot_text = ' '.join(bot_res['text'])
    #     voice_bytes = tts.get_audio_bytes_stream(bot_text)
    #     print("playing audio.. / emmitting voice")
    #     sd.play(np.frombuffer(voice_bytes, dtype=np.int16), 22000)
    # else:
    #     print('no text')
    # bot_commands = bot_res.get('commands')
    # if bot_commands:
    #     if bot_commands[0].get('sample'):
    #         print("tagging a sample scenario")
    #         stt.set_sample_tagging_focus()
    #     elif bot_commands[0].get('Sample Details'):
    #         print("sample tagging finished")
    #         # TODO consider case of termination
    #         stt.set_regular_focus()
    #     print('emitting action', bot_res.get('commands'))
    # else:
    #     print('no commands')

# filename = filenames[int(92)-1]

# print("filename:", filename)
# f = open(f'{samples_path}/{filename}', mode='rb')
# audio = f.read()

# print("total length in bytes:", len(audio))
# print("playing audio..")
# sd.play(np.frombuffer(audio, dtype=np.int16), 16000)
# # sd.wait()

# stt.create_stream()
# stt_res = stt.process_audio_stream(audio)
# print('User:', str(stt_res))
# print('audiobuffer: ', len(stt.buffered_data))
# print('audiofeed debug', stt.debug_feed)
# print('total debug', stt.debug_total)
# print('voice debug', stt.debug_voice)
# print('silence debug', stt.debug_silence)

# frame_size = 2048//2//3 + 1
# print('Frame Size', frame_size)
# for i in range(0, len(audio), frame_size):
#     chunk = audio[i:i+frame_size]
#     if len(chunk) < frame_size:
#         break
#     result = stt.process_audio_stream(chunk)
#     if result is not None:
#         print("result", result)

# print("leftover chunks", len(chunk))
# print('total debug', stt.debug_total)
# print('voice debug', stt.debug_voice)
# print('silence debug', stt.debug_silence)
sd.wait()