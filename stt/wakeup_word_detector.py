import pvporcupine
import sys
import struct
from threading import Thread
from .data_buffer import DataBuffer

class WakeUpVoiceDetector(Thread):

    def __init__(
            self,
            access_key = 
                [
                    "9DG6ZfAltia6TEuOiU/IImtAsttIfCeyxpks3SuNVbOY8LWkbOSjHQ==",
                    "ABrqFVk5qLvuLQjkGQx+fWTQwRWAt57Yc2BI0JbzZ4odNwe6JXXiZQ=="
                ],
            keyword_paths = [
                [
                    "models/pvprocupine/%s/sen-va_en_windows_v2_2_0/sen-va_en_windows_v2_2_0.ppn",
                    "models/pvprocupine/%s/Hello-Eva_en_windows_v2_2_0/Hello-Eva_en_windows_v2_2_0.ppn"
                ],
                ["models/pvprocupine/%s/sen-va_en_linux_v2_2_0/sen-va_en_linux_v2_2_0.ppn"]
            ],
            sensitivities=None):
        super(WakeUpVoiceDetector, self).__init__()

        try:
            if sys.platform.startswith('linux'):
                keyword_paths = keyword_paths[1]
            elif sys.platform.startswith('win'):
                keyword_paths = keyword_paths[0]
                print(f'Keywords set {keyword_paths}')
            else:
                raise NotImplementedError()
        except:
            raise Exception("Unsupported Platform")    

        alternate_i = 0
        initialized = False
        while not initialized:
            self._access_key = access_key[alternate_i]
            self._keyword_paths = [k % alternate_i for k in keyword_paths]
            print(f'Trying keywords_paths {keyword_paths}')
            self._sensitivities = sensitivities
            try:            
                self.porcupine_handle = pvporcupine.create(
                        access_key=self._access_key,
                        keyword_paths=self._keyword_paths,
                        sensitivities=self._sensitivities)
                initialized = True
            except:
                print('Reswitching Access Key')
                alternate_i += 1 
                
        
        self.frame_size = 1024
        self.buffer = DataBuffer(self.frame_size)
        # self.reset_data_buffer()
    
    def reset_data_buffer(self):
        self.buffer.reset()

    def process_audio_stream(self, audio_packet): 
        # Utilize full audio_packet instead
        self.buffer.add(audio_packet)
        for frame in self.buffer:
            # Process only proper frame sizes
            if len(frame) < self.frame_size:
                break
            # print("\nProcessing", flush=True)
            pcm = struct.unpack_from("h" *self.porcupine_handle.frame_length, frame.bytes)
            result = self.porcupine_handle.process(pcm)
            if result >= 0:
                self.reset_data_buffer()
                return True