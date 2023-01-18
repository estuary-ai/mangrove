"""
TODO logic to be transfered to the following files:
- `assistant_controller.py`
- `receiver.py`
- `storage_manager.py`

"""

import os
import time
import json
from threading import Thread

import numpy as np
import sounddevice as sd
from flask import Flask
from flask_socketio import SocketIO
from stt import WakeUpVoiceDetector, STTController
from bot import BotController
from tts import TTSController

# import tensorflow as tf
# tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
    
SAMPLE_RATE = 16000
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app,
    cors_allowed_origins='*',
    cors_credentials=True)
    
@socketio.on('connect')
def handle_connect():
    global session_audio_buffer
    global command_audio_buffer
    global writing_files_threads_list
    global indicator_bool
    session_audio_buffer = b""
    command_audio_buffer = b""
    writing_files_threads_list = []
    indicator_bool = True
    stt.create_stream()
    write_output('client connected')

@socketio.on('disconnect')
def handle_disconnect():
    global is_sample_tagging
    global command_audio_buffer
    global writing_files_threads_list
    is_sample_tagging = False

    for thread in writing_files_threads_list:
        thread.join()

    if len(command_audio_buffer) > 0:
        sd.play(np.frombuffer(command_audio_buffer, dtype=np.int16), 16000)

    # sd.play(np.frombuffer(session_audio_buffer, dtype=np.int16), 16000)
    
    session_id = str(int(time.time()*1000))
    with open(f"sample-audio-binary/{session_id}_binary.txt", mode='wb') as f:
        f.write(session_audio_buffer)

    # write_output('debug, testing the whole audio of the session')
    stt.reset_audio_stream()
    # stt.create_stream()
    # result = stt.process_audio_stream(session_audio_buffer)
    # write_output(result)

    write_output('client disconnected')

def setup_sample_tagging():
    write_output('set in sample tagging')
    global is_sample_tagging
    is_sample_tagging = True
    stt.set_sample_tagging_focus()

def kill_sample_tagging():
    write_output('kill sample tagging')
    global is_sample_tagging
    is_sample_tagging = False
    stt.set_regular_focus()
    stt.reset_audio_stream()
    # TODO consider also case of termination using exit word

@socketio.on('read-tts')
def handle_tts_read(data):
    data = json.loads(str(data))
    write_output("request to read data " + str(data))
    audioBytes = tts.get_feature_read_bytes(data['feature'],
                                            data['values'],
                                            data['units'])
    socketio.emit("bot-voice", audioBytes)

@socketio.on('stream-wakeup')
def handle_stream_wakeup(data):
    wakeUpWordDetected = wakeUpWordDetector.process_audio_stream(data)
    if wakeUpWordDetected:
        write_output("detected wakeup word")
        socketio.emit('wake-up')    

def write_to_file(text, command_audio_buffer):
    def write(text, command_audio_buffer):
        with open(f"sample-audio-binary/{text.replace(' ', '_')}_binary.txt", mode='wb') as f:
            f.write(command_audio_buffer)
    thread = Thread(target=write, args=(text, command_audio_buffer))
    thread.start()
    writing_files_threads_list.append(thread)

def print_feeding_indicator():
    global indicator_bool
    indicator = "\\" if indicator_bool else  "/"
    write_output('=', end="")
    indicator_bool = not indicator_bool



@socketio.on('stream-audio')
def handle_stream_audio(data):
    global stt_res_buffer
    stt_res_buffer = None
    global command_audio_buffer
    global session_audio_buffer
    if len(command_audio_buffer) == 0:
        write_output("recieving first stream of audio command")
    
    data = bytes(data)
    command_audio_buffer += data
    session_audio_buffer += data

    stt_res = stt.process_audio_stream(data)
    if(len(command_audio_buffer) % len(data)*10 == 0):
        print_feeding_indicator()
        # write_output(f"={stt.debug_silence_state}=", end="")

    if stt_res is not None:
        write_output('User: ' + str(stt_res))
        socketio.emit('stt-response', stt_res)
        # stt.unlock_stream()
        
        global is_sample_tagging
        if is_sample_tagging:
            write_output("is sample taggin on..")
            # TERMINATION SCHEME BY <OVER> IN SAMPLE-TAGGING
            if stt_res_buffer is not None:
                write_output("appending to buffer - sample tagging")
                stt_res_buffer = stt._combine_outcomes([stt_res_buffer, stt_res])
            stt_res_buffer = stt_res
            if not ("over" in stt_res['text'].rstrip()[-30:]):
                return                
            stt_res = stt_res_buffer
            stt_res_buffer = None
                    
        write_to_file(stt_res['text'], command_audio_buffer)
        command_audio_buffer = b""

        bot_res = bot.send_user_message(stt_res['text'])
        print('SENVA: ' + str(bot_res))    
        
        bot_texts = bot_res.get('text')
        if bot_texts is not None:
            voice_bytes = tts.get_audio_bytes_stream(' '.join(bot_texts))
            write_output('emmiting bot-voice')
            socketio.emit('bot-voice', voice_bytes)
        else:
            print('no text')

        check_bot_commands(bot_res)

        write_output("emitting bot-response")
        socketio.emit('bot-response', bot_res)


def check_bot_commands(bot_res):
    bot_commands = bot_res.get('commands')
    if bot_commands is not None and len(bot_commands) > 0:
        sample_command = bot_commands[0].get('sample')
        sample_details_command =  bot_commands[0].get('sample_details')
        if sample_details_command is not None:
            write_output("sample tagging finished successfully")
            kill_sample_tagging()
        elif sample_command is not None:
            write_output("tagging a sample scenario")
            setup_sample_tagging()
        elif sample_command is not None and sample_command is False:
            write_output("sample tagging exited")
            kill_sample_tagging()
        write_output('emitting commands ' +  str(bot_res.get('commands')))
    else:
        print('no commands')


@socketio.on('reset-audio-stream')
def handle_reset_audio_stream():
    stt.reset_audio_stream()

@socketio.on('trial')
def handle_trial(data):
    write_output('received trial: ' + data)

@socketio.on_error_default  # handles all namespaces without an explicit error handler
def default_error_handler(e):
    write_output('error debug', e)
    stt.reset_audio_stream()
    # TODO reset anything 

def write_output(msg, end='\n'):
    print(str(msg), end=end, flush=True)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Personal information')
    parser.add_argument('--cpu', dest='cpu', type=bool, default=False, help='Use CPU instead of GPU')
    parser.add_argument('--port', dest='port', type=int, default=4000, help='Use CPU instead of GPU')
    args = parser.parse_args()
    
    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    print("Initializing WakeUpWordDetector")
    wakeUpWordDetector = WakeUpVoiceDetector()
    print("Initializing STT Controller")
    stt = STTController()
    stt.set_regular_focus()
    is_sample_tagging = False
    print("Initializing Bot Controller")
    bot = BotController()
    print("Initializing TTS Controller")
    tts = TTSController()    
    print("Server is about to be Up and Running..")

    socketio.run(app, host='0.0.0.0', port=args.port)    