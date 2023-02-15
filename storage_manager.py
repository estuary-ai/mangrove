from os import path
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
        
    def write_audio_file(self, text, command_audio_buffer):
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
        
    def ensure_completion(self):
        for thread in self.threads_pool:
            thread.join()
            
def write_output(msg, end='\n'):
    print(str(msg), end=end, flush=True)
    