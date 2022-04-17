from flask import Flask, render_template
from flask_socketio import SocketIO
# from mic_vad_streaming
import webrtcvad
import deepspeech
import collections
import time
import numpy as np
import sys


'''==============================='''
'''========= DM IMPORTS =========='''

import asyncio
import pyttsx3
import os

from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig

'''==============================='''
'''====== DM INITIALIZATION ======'''

agent = Agent.load("models/model.tar.gz", action_endpoint=EndpointConfig('http://localhost:5055/webhook'))
engine = pyttsx3.init()
engine.setProperty('rate', 120)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)

if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

'''==============================='''


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app,
    cors_allowed_origins='*',
    cors_credentials=True)
    
silence_buffers = collections.deque(maxlen=2)
SAMPLE_RATE = 16000
VAD_AGGRESSIVENESS = 3
SILENCE_THRESHOLD = 200 
# ms of inactivity before processing the audio
vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
MODEL_DIR = '../model/deepspeech-0.9.3-models'
model = deepspeech.Model(MODEL_DIR + ".pbmm")
model.enableExternalScorer(MODEL_DIR + ".scorer")
silence_start = None


def create_stream():
    global stream_context
    global recorded_chunks 
    global recorded_audio_length
    stream_context = model.createStream()
    recorded_chunks = 0
    recorded_audio_length = 0

def reset_silence_buffer():
    global silence_buffers
    silence_buffers = collections.deque(maxlen=2)

def add_buffered_silence(data):
    global silence_buffers
    if len(silence_buffers):
        silence_buffers.append(data)
        total_length = 0
        for buf in silence_buffers:
            total_length += len(buf)
        # TODO this should not be a list but a byte like object or string!
        audio_buffer = b''.join(silence_buffers)
        print(type(audio_buffer))
        reset_silence_buffer()
    else:
        audio_buffer = data
    return audio_buffer    

def feed_audio_content(data):
    global recorded_audio_length
    global stream_context
    recorded_audio_length += int((len(data)/2) * (1/16000) * 1000)
    stream_context.feedAudioContent(np.frombuffer(data, np.int16))

def process_voice(data):
    global recorded_chunks
    global silence_start
    silence_start = None
    if recorded_chunks == 0:
        print("", flush=True)
        sys.stdout.write('[start]') # recording started
    else:
        sys.stdout.write('=') # still recording
    recorded_chunks += 1
    data = add_buffered_silence(data)
    feed_audio_content(data)

def finish_stream():
    global stream_context
    global recorded_audio_length
    if stream_context:
        start = round(time.time() * 1000)
        transcription = stream_context.finishStream()
        if transcription:
            print("", flush=True)
            print("Recognized Text:", transcription, flush=True)
            recog_time = round(time.time() * 1000) - start
            return { 
                'text': transcription,
                'recog_time': recog_time,
                'recorded_audio_length':recorded_audio_length
                }
    reset_silence_buffer()
    stream_context = None

def intermediate_decode():
    results = finish_stream()
    create_stream()
    return results

def process_silence(data):
    global recorded_chunks
    global silence_start
    if recorded_chunks > 0: # recording is on
        sys.stdout.write('-') # silence detected while recording
        feed_audio_content(data)
        
        if silence_start is None:
            silence_start = round(time.time() * 1000)
        else:
            now = round(time.time() * 1000)
            if now - silence_start > SILENCE_THRESHOLD:
                silence_start = None
                print("\n[end]", flush=True)
                results = intermediate_decode()
                return results

    else:
        # VAD has a tendency to cut the first bit of audio data 
        # from the start of a recording
	    # so keep a buffer of that first bit of audio and 
        # in addBufferedSilence() reattach it to the beginning of the recording
        sys.stdout.write('.') # silence detected while not recording
        silence_buffers.append(data)


def process_audio_stream(data):
    # print(len(data))
    is_speech = vad.is_speech(data, SAMPLE_RATE)
    if is_speech:
        process_voice(data)
    else:
        return process_silence(data)

    # // timeout after 1s of inactivity
	# clearTimeout(endTimeout);
	# endTimeout = setTimeout(function() {
	# 	console.log('timeout');
	# 	resetAudioStream();
	# },1000);

@socketio.on('connect')
def handle_connect():
    print('client connected', flush=True)
    create_stream()
    
@socketio.on('disconnect')
def handle_disconnect():
	print('client disconnected', flush=True)

@socketio.on('stream-data')
def handle_stream_data(data):
    # print('audiostream', len(data))
    results = process_audio_stream(data)
    if results:
        print('results', results, flush=True)

        #Assuming that results is a string containing transcripted speech
        response = sendUserMessage({'Body': results, 'From': 'Neil'})       #get correct user ID

        #Sending audio/commands/text back to Hololens
        socketio.emit('recognize', response)

'''==============================='''
'''========== DM CODE ============'''

def sendUserMessage(request):

    user_message = request.get('Body')
    conversation_id = request.get('From')

    #Sending message to RASA
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    messages = loop.run_until_complete(agent.handle_text(user_message, sender_id=conversation_id))
    loop.close()

    #Deciphering RASA's response
    audio_files = []
    texts = []
    commands = []
    audio_present = False
    
    for message in messages:
        if 'text' in message:
            audio_present = True
            text = message['text']
            texts.append(text)
            engine.save_to_file(text , f'output_{len(audio_files) + 1}.wav')
            audio_files.append(f'output_{len(audio_files) + 1}.wav')
            engine.runAndWait()
        elif 'custom' in message:
            commands.append(message['custom'])

    #Compiling responses
    response = {}
    if audio_present:
        audio_data = []
        for audio_file in audio_files:
            with open(audio_file, 'rb') as f:
                audio_data.append(f.read())
            os.remove(audio_file)
        response['audio'] = audio_data

    response['text'] = texts
    response['commands'] = commands

    return response

'''==============================='''
	
@socketio.on('stream-end')
def handle_stream_end():
    print("\n[end]", flush=True)
    results = intermediate_decode()
    print('stream-end', results)
    if results:
        print('results', results, flush=True)
        socketio.emit('recognize', results)

def reset_audio_stream():
	# clearTimeout(endTimeout)
    global recorded_chunks
    global silence_start
    print('\n[reset]', flush=True)
    intermediate_decode() # ignore results
    recorded_chunks = 0
    silence_start = None

@socketio.on('stream-reset')
def handle_stream_reset():
    reset_audio_stream()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=4000)