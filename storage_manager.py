import time
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
        self.threads_pool = []
        if not path.exists(self.audio_files_dir):
            makedirs(self.audio_files_dir)
    
    def _enqueue_task(self, func, *args):
        self = StorageManager()
        thread = Thread(
            target=func, 
            args=args
        )
        thread.start()
        self.threads_pool.append(thread)
        
    @classmethod
    def play_audio_packet(self, audio_packet, transcription=None, block=False):
        def play_save_packet(audio_packet, transcription=None):
            write_output('Here is response frames played out.. pay attention')
            sd.play(np.frombuffer(audio_packet.bytes, dtype=np.int16), 16000)
            sd.wait()
            if transcription is not None:
                with open(f"sample-audio-binary/{transcription}_{str(time.time())}.txt", mode='wb') as f:
                    f.write(audio_packet.bytes)
                
        # TODO Write meta data too
        self = StorageManager()
        if block:
            play_save_packet(audio_packet, transcription)
        else:
            self._enqueue_task(play_save_packet, audio_packet, transcription)
        
    @classmethod
    def write_audio_file(self, audio_buffer, text='', include_session_id=False):
        self = StorageManager()
        def _write(audio_buffer, text, prefix):
            # sd.play(np.frombuffer(session_audio_buffer, dtype=np.int16), 16000)        
            with open(
                path.join(
                    self.audio_files_dir, 
                    f'{prefix}{text.replace(" ", "_")}_binary.txt'
                ),
                mode='wb'
            ) as f:
                f.write(audio_buffer.bytes)
                
        prefix = str(int(time.time()*1000)) if include_session_id else ""
        self._enqueue_task(_write, audio_buffer, text, prefix)
    
    @classmethod
    def ensure_completion(self):
        self = StorageManager()
        for i, thread in enumerate(self.threads_pool):
            if not thread:
                write_output(f'Discarding none valid thread # {i}')
                continue
            thread.join()
            
def write_output(msg, end='\n'):
    print(str(msg), end=end, flush=True)
    