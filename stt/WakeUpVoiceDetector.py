from threading import Thread
import pvporcupine

import struct

class WakeUpVoiceDetector(Thread):

    def __init__(
            self,
            access_key = "2aUEVaMWbCb6t+Q/o87vQtMX+ITUoMB65242NNDC3qtXxxbwIkzqEA==",
            keyword_paths = ["models/Hello-eva_en_windows_v2_1_0.ppn"],
            sensitivities=None):

        super(WakeUpVoiceDetector, self).__init__()
        self._access_key = access_key
        self._library_path =pvporcupine.LIBRARY_PATH
        self._model_path = pvporcupine.MODEL_PATH
        self._keyword_paths = keyword_paths
        self._sensitivities = sensitivities

        self.porcupine = pvporcupine.create(
                access_key=self._access_key,
                library_path=self._library_path,
                model_path=self._model_path,
                keyword_paths=self._keyword_paths,
                sensitivities=self._sensitivities)

        self.frame_size = 1024
        self.reset_data_buffer()


    def reset_data_buffer(self):
            self.buffered_data = b""

    def process_audio_stream(self, new_data):         
        data_stream = self.buffered_data + new_data 
        self.reset_data_buffer()

        i = 0
        while i < len(data_stream):
            sub_data = data_stream[i:i+self.frame_size]
            # Process only proper frame sizes
            if len(sub_data) < self.frame_size:
                break
            # print("\nProcessing", flush=True)
            pcm = struct.unpack_from("h" *self.porcupine.frame_length, sub_data)
            result = self.porcupine.process(pcm)
            if result >= 0:
                self.reset_data_buffer()
                return True
            i += self.frame_size
        
        self.buffered_data = data_stream[i:]