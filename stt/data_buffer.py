import numpy as np
import sounddevice as sd
from functools import reduce
from .audio_packet import AudioPacket
from queue import PriorityQueue

class DataBuffer:
    def __init__(self, frame_size=320, max_queue_size=100):
        # num_padding_frames = int(padding_duration_ms / frame_duration_ms)
        # ring_buffer = collections.deque(maxlen=num_padding_frames)
        self.max_queue_size = max_queue_size
        self.queue = PriorityQueue(maxsize=self.max_queue_size)
        self.frame_size = frame_size
        self.queue_before_reset = None
        
    def reset(self):
        with self.queue.mutex:
            self.queue_before_reset = self.queue.queue
        self.queue = PriorityQueue(maxsize=self.max_queue_size)

    def __str__(self):
        return ' '.join([str(packet) for packet in self.queue.queue])
 
    def add(self, audio_packet: AudioPacket):
        self.queue.put(audio_packet)

    def get_frame(self):
        data: AudioPacket = AudioPacket.get_null_packet()
        # self.queue.mutex.acquire()
        while (len(data) < self.frame_size) and self.queue.qsize():
            new_packet = self.queue.get()
            data += new_packet
        if len(data) < self.frame_size:
            if len(data) > 0:
                self.add(data)
            raise StopIteration()
        frame = data[:self.frame_size]
        leftover = data[self.frame_size:]
        self.queue.put(leftover)
        # self.queue.mutex.release()
        return frame
    
    def __next__(self):
        return self.get_frame()
        
    
    def __iter__(self):
        return self

    def __len__(self):
        return len(self.queue.qsize())

    def _debug_verify_order(self):
        with self.queue.mutex:
            # noise_fstamps = []
            # noise_estamps = []
            for i in range(self.queue.qsize - 1):
                try:
                    assert self.queue.queue[i] > self.queue.queue[i+1]
                except:
                    try:
                        assert self.queue.queue[i].timestamp == self.queue.queue[i+1].timestamp
                        print(f'same {i} == {i+1}')
                    except:
                        print(f'error at {i}, and {i+1}')
                
    def _debug_play_buffer(self):
        with self.queue.mutex:
            packet = reduce(lambda x,y : x+y, self.queue.queue)
            sd.play(np.frombuffer(packet.bytes, dtype=np.int16),16000)