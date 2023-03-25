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
    
    @classmethod
    def write_audio_file(self, text, command_audio_buffer):
        self = StorageManager()
        def write(text, audio_buffer):
            with open(
                path.join([
                    self.audio_files_dir, 
                    f'{text.replace(" ", "_")}_binary.txt'
                ]),
                mode='wb'
            ) as f:
                f.write(audio_buffer)
        thread = Thread(
            target=write, 
            args=(text, command_audio_buffer)
        )
        thread.start()
        self.threads_pool.append(thread)
    
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
    