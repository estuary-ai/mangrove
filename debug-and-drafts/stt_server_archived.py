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

from STTController import STTController
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
    
@socketio.on('connect')
def handle_connect():
    print('client connected', flush=True)
    stt.create_stream()
    
@socketio.on('disconnect')
def handle_disconnect():
	print('client disconnected', flush=True)

@socketio.on('stream-data')
def handle_stream_data(data):
    # print('audiostream', len(data))
    results = stt.process_audio_stream(data)
    if results:
        print('results', results['text'], flush=True)

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
    results = stt.intermediate_decode()
    print('stream-end', results)
    if results:
        print('results', results, flush=True)
        socketio.emit('recognize', results)

@socketio.on('stream-reset')
def handle_stream_reset():
    stt.reset_audio_stream()

if __name__ == '__main__':
    print("Init STT model")
    stt = STTController()
    socketio.run(app, host='0.0.0.0', port=4000)