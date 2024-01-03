import os
import re
import time
import wave
import numpy as np
import sounddevice as sd
from threading import Thread
# from stt import AudioPacket


BLACK_BOX_DIR = 'blackbox'
IMAGES_DIR = os.path.join(BLACK_BOX_DIR, 'sample-images')
COMMANDS_CACHE_DIR = os.path.join(BLACK_BOX_DIR, 'sample-audio-binary')
LOG_DIR = os.path.join(BLACK_BOX_DIR, 'logs')
WORLD_STATE_DIR = os.path.join(BLACK_BOX_DIR, 'world-state')
GENERATED_AUDIO_DIR = os.path.join(BLACK_BOX_DIR, 'generated-audio')

for dir in [
    IMAGES_DIR, COMMANDS_CACHE_DIR, LOG_DIR,
    WORLD_STATE_DIR, GENERATED_AUDIO_DIR
]:
    if not os.path.exists(dir):
        os.makedirs(dir)

class StorageManager:
    """ Storage manager for audio and images """

    _self = None

    def __new__(cls):
        """ Singleton pattern """
        if cls._self is None:
            cls._self = super().__new__(cls)
        return cls._self

    def __init__(self):
        self.threads_pool = []

    @classmethod
    def establish_session(cls):
        """ Establish session, generate session id and open log file """
        cls = StorageManager()
        cls._generate_session_id()

    def _generate_session_id(self):
        """ Generate session id and open log file"""
        try:
            self.log_file.close()
        except:
            # No log file open
            pass
        self.session_id = str(time.time())
        self.log_file = open(os.path.join(LOG_DIR, f'session_{self.session_id}.log'), mode='w')

    @classmethod
    def clean_up(cls):
        """ Clean up upon disconnection and delegate logging"""
        cls = StorageManager()
        try:
            cls.log_file.close()
        except:
            # No log file open
            write_output('No log file open to close.')

    def _enqueue_task(self, func, *args):
        """ Enqueue task to thread pool

        Args:
            func (function): Function to execute
            *args: Arguments to pass to function
        """
        self = StorageManager()
        thread = Thread(
            target=func,
            args=args
        )
        thread.start()
        self.threads_pool.append(thread)

    @classmethod
    def play_audio_packet(cls, audio_packet, transcription=None, block=False):
        def play_save_packet(audio_packet, transcription=None):
            write_output('Here is response frames played out.. pay attention')
            sd.play(audio_packet.float, 16000)
            sd.wait()
            # if transcription is not None:
            #     session_id = f'session_{int(time.time()*1000)}_'
            #     with open(os.path.join(COMMANDS_CACHE_DIR, f"{transcription}_{session_id}.txt"), mode='wb') as f:
            #         f.write(audio_packet.bytes)

        # TODO Write meta data too
        cls = StorageManager()
        if block:
            play_save_packet(audio_packet, transcription)
        else:
            cls._enqueue_task(play_save_packet, audio_packet, transcription)

    def _write_bin(self, audio_buffer, text, prefix):
        # sd.play(np.frombuffer(session_audio_buffer, dtype=np.int16), 16000)
        with open(
            os.path.join(
                COMMANDS_CACHE_DIR,
                f'{prefix}{text.replace(" ", "_")}_binary.txt'
            ),
            mode='wb'
        ) as f:
            f.write(audio_buffer.bytes)

    def _write_wav(self, audio_buffer, text, prefix):
        """ Write audio file to disk as wav

        Args:
            audio_buffer (AudioPacket): Audio packet to write
            text (str): Text (transcription) to use as file name
            prefix (str): Prefix of file name

        """
        # sd.play(np.frombuffer(session_audio_buffer, dtype=np.int16), 16000)
        with wave.open(
            os.path.join(
                COMMANDS_CACHE_DIR,
                f'{prefix}{text.replace(" ", "_")}.wav'
            ),
            mode='w'
        ) as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(
                np.frombuffer(audio_buffer.bytes, dtype=np.int16)
            )

    @classmethod
    def write_audio_file(self, audio_buffer, text='', format='wav'):
        """ Write audio file to disk"""
        self = StorageManager()

        _write = {
            'binary': lambda a, t, p:  self._write_bin(a, t, p),
            'wav': lambda a, t, p:  self._write_wav(a, t, p),
        }

        session_id = f'session_{int(time.time()*1000)}_'
        self._enqueue_task(_write[format], audio_buffer, text, session_id)

    @classmethod
    def ensure_completion(self):
        """Ensure all threads are completed"""
        self = StorageManager()
        for i, thread in enumerate(self.threads_pool):
            if not thread:
                write_output(f'Discarding none valid thread # {i}')
                continue
            thread.join()

    def log_state(self, state):
        """ Log state to file"""
        self = StorageManager()
        def _write_state(state):
            self.log_file.write(str(state))
            self.log_file.flush()
        self._enqueue_task(_write_state, state)

    def get_generated_audio_path(self, text):
        """ Get generated audio path from text"""
        generation_id = f'generation_{int(time.time()*1000)}_'
        text_substring = re.sub(r'[^\w_. -]', '_', text.replace(" ", "_"))
        return os.path.join(GENERATED_AUDIO_DIR, f'{generation_id}{text_substring}.wav')


def write_output(msg, end='\n'):
    """ Write output to console with flush"""
    print(str(msg), end=end, flush=True)

