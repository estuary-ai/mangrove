import time
import wave
import numpy as np
import sounddevice as sd   
from os import path, makedirs
from threading import Thread

class StorageManager:
    
    _self = None

    def __new__(cls):
        if cls._self is None:
            cls._self = super().__new__(cls)
        return cls._self
    
    def __init__(self):
        self.audio_files_dir = 'sample-audio-binary'
        self.logging_dir = 'world-state-logs'
        self.threads_pool = []
        if not path.exists(self.audio_files_dir):
            makedirs(self.audio_files_dir)
        if not path.exists(self.logging_dir):
            makedirs(self.logging_dir)
    
    @classmethod
    def establish_session(cls):
        cls = StorageManager()
        cls._generate_session_id()

    def _generate_session_id(self):
        try:
            self.log_file.close()
        except:
            # No log file open
            pass
        self.session_id = str(time.time())
        self.log_file = open(f'session_{self.session_id}.log', mode='w')
    
    def clean_up(cls):
        cls = StorageManager()
        try:
            cls.log_file.close()
        except:
            # No log file open
            write_output('No log file open to close.')
        
    def _enqueue_task(self, func, *args):
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
            sd.play(np.frombuffer(audio_packet.bytes, dtype=np.int16), 16000)
            sd.wait()
            if transcription is not None:
                with open(f"sample-audio-binary/{transcription}_{cls.session_id}.txt", mode='wb') as f:
                    f.write(audio_packet.bytes)
                
        # TODO Write meta data too
        cls = StorageManager()
        if block:
            play_save_packet(audio_packet, transcription)
        else:
            cls._enqueue_task(play_save_packet, audio_packet, transcription)
        
    def _write_bin(self, audio_buffer, text, prefix):
        # sd.play(np.frombuffer(session_audio_buffer, dtype=np.int16), 16000)        
        with open(
            path.join(
                self.audio_files_dir, 
                f'{prefix}{text.replace(" ", "_")}_binary.txt'
            ),
            mode='wb'
        ) as f:
            f.write(audio_buffer.bytes)
        
    def _write_wav(self, audio_buffer, text, prefix):
        # sd.play(np.frombuffer(session_audio_buffer, dtype=np.int16), 16000)        
        with wave.open(
            path.join(
                self.audio_files_dir, 
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
        self = StorageManager()
        
        _write = {
            'binary': lambda a, t, p:  self._write_bin(a, t, p),
            'wav': lambda a, t, p:  self._write_wav(a, t, p),
        }
        
        session_id = f'session_{int(time.time()*1000)}_'
        self._enqueue_task(_write[format], audio_buffer, text, session_id)
    
    @classmethod
    def ensure_completion(self):
        self = StorageManager()
        for i, thread in enumerate(self.threads_pool):
            if not thread:
                write_output(f'Discarding none valid thread # {i}')
                continue
            thread.join()
            
    def log_state(self, state):
        self = StorageManager()
        def _write_state(state):
            self.log_file.write(str(state))
            self.log_file.flush()
        self._enqueue_task(_write_state, state)
        
            
def write_output(msg, end='\n'):
    print(str(msg), end=end, flush=True)
    
    