import json
import numpy as np
from typing import TypeVar, Type

DEFAULT_SAMPLERATE = 16000

AudioPacket = TypeVar('AudioPacket', bound='AudioPacket')
class AudioPacket(object):
    """Represents a "Packet" of audio data."""
    def __init__(self, data_json, is_processed=False):        
        if not isinstance(data_json, dict):
            data_json = json.loads(str(data_json))
        
        self.sample_rate = data_json['sampleRate']
        self.num_channels = data_json['numChannels']
        self.timestamp = data_json['timestamp'] # MS
        
        if not is_processed:
            buffer = np.array(data_json['audio'])
                
            self.bytes = self.preprocess_audio_buffer(
                buffer, self.sample_rate, self.num_channels
            )   
        else:
            self.bytes = data_json['bytes']
        
        self.frame_size = len(self.bytes)
        self.duration = ((self.frame_size/16000)/2.0)*1000
        self.id = data_json.get('packetID')
    
    def preprocess_audio_buffer(self, buffer, sample_rate, num_channels):
        # Merge Channels if > 1
        one_channel_buffer = np.zeros(len(buffer)//num_channels)
        channel_contribution = 1/num_channels

        for i in range(len(one_channel_buffer)):
            for channel_i in range(num_channels):
                one_channel_buffer[i] +=\
                    buffer[i*num_channels + channel_i]*channel_contribution     
        
        # Downsample if necesssary
        division = sample_rate//DEFAULT_SAMPLERATE
        buffer_16k_1ch = np.zeros(int(np.ceil(len(one_channel_buffer)/division)))
        if division > 1:
            for i in range(len(buffer_16k_1ch)):
                buffer_16k_1ch[i] = one_channel_buffer[i*division]                
        else:
            buffer_16k_1ch = one_channel_buffer
        # TODO revise division if < 1

        # Convert to int16 with scaling
        # https://gist.github.com/HudsonHuang/fbdf8e9af7993fe2a91620d3fb86a182    
        dtype = np.dtype('int16')
        i = np.iinfo(dtype)
        abs_max = 2 ** (i.bits - 1)
        offset = i.min + abs_max
        buffer_int16 = (buffer_16k_1ch * abs_max + offset).clip(i.min, i.max).astype(dtype)
        
        return bytes(buffer_int16)    
    
    def __add__(self, __audio_packet: Type[AudioPacket]):
        # ensure no errs, and snippets are consecutive
        if self > __audio_packet:
            raise Exception(
                f"Audio Packets are not in order: {self.timestamp} > {__audio_packet.timestamp}"
            )
        
        timestamp = self.timestamp
        if self.bytes == b'': # DUMMY
            timestamp = __audio_packet.timestamp
            
        return AudioPacket(
            {
            "bytes": self.bytes + __audio_packet.bytes,
            "timestamp": timestamp,
            "sampleRate": self.sample_rate,
            "numChannels": self.num_channels
            },
            is_processed=True
        )
    
    def __calculate_new_timestamp(self, start_byte_idx):
        offset = (start_byte_idx/len(self.bytes)) * self.duration
        return self.timestamp + offset
    
    def __getitem__(self, key):
        if isinstance(key, slice):
            # Note that step != 1 is not supported
            start, stop, step = key.indices(len(self))
            return AudioPacket(
                {
                    "bytes": self.bytes[start:stop],
                    "timestamp": self.__calculate_new_timestamp(start),
                    "sampleRate": self.sample_rate,
                    "numChannels": self.num_channels
                },
                is_processed=True
            ) 
            
        elif isinstance(key, int):
            raise (NotImplementedError, "value as index; only slices")
        elif isinstance(key, tuple):
            raise (NotImplementedError, "Tuple as index; only slices")
        else:
            raise (TypeError, 'Invalid argument type: {}'.format(type(key)))
    
    def __str__(self) -> str:
        return (self.timestamp, self.duration, len(self.bytes))
    
    def __eq__(self, __o: object) -> bool:
        return self.timestamp == __o.timestamp and\
            self.bytes == __o.bytes

    def __lt__(self, __o: object) -> bool:
        # TODO verify + duration work
        # return self.timestamp + self.duration <= __o.timestamp
        return self.timestamp < __o.timestamp

    def __gt__(self, __o: object) -> bool:
        # return self.timestamp >= __o.timestamp + __o.duration
        return self.timestamp > __o.timestamp

    def __ne__(self, __o: object) -> bool:
        return not(self.__eq__(self, __o))
    
    def __len__(self) -> int:
       return len(self.bytes) 
   
    @staticmethod
    def get_null_packet():
        return AudioPacket(
            {
                "bytes": b"",
                "timestamp": 0,
                "sampleRate": DEFAULT_SAMPLERATE,
                "numChannels": 1            
            },
            is_processed=True
        )