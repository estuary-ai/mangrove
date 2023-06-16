import numpy as np
import sounddevice as sd
from functools import reduce
from .audio_packet import AudioPacket
from queue import PriorityQueue

class DataBuffer:
    """Data buffer for audio packets"""
    def __init__(self, frame_size=320, max_queue_size=100):
        """Initialize data buffer
        
        Args:
            frame_size (int, optional): Number of bytes to read from queue. Defaults to 320.
            max_queue_size (int, optional): Maximum number of audio packets to store in queue. Defaults to 100.
        """
        self.max_queue_size = max_queue_size
        self.queue = PriorityQueue(maxsize=self.max_queue_size)
        self.default_frame_size = frame_size
        self.queue_before_reset = None
        
    def reset(self):
        """Reset queue to empty state"""
        with self.queue.mutex:
            self.queue_before_reset = self.queue.queue
        self.queue = PriorityQueue(maxsize=self.max_queue_size)

    def __str__(self):
        return ' '.join([str(packet) for packet in self.queue.queue])
 
    def add(self, audio_packet: AudioPacket):
        """Add audio packet to queue
        
        Args:
            audio_packet (AudioPacket): Audio packet to add to queue
        """
        self.queue.put(audio_packet)

    def read(self, frame_size=None):
        """Get next frame of audio packets from queue given frame size 

        Args:
            frame_size (int, optional): Number of bytes to read from queue. Defaults to self.default_frame_size.
        
        Returns:
            AudioPacket: Audio packet of size frame_size
        
        Raises:
            StopIteration: If queue is empty or if there is not enough data in queue to read frame_size bytes
        """
        frame_size = frame_size or self.default_frame_size
        data: AudioPacket = AudioPacket.get_null_packet()
        # self.queue.mutex.acquire()
        while (len(data) < frame_size) and self.queue.qsize():
            new_packet = self.queue.get()
            data += new_packet
        if len(data) < frame_size:
            if len(data) > 0:
                self.add(data)
            return None
        frame = data[:frame_size]
        leftover = data[frame_size:]
        self.queue.put(leftover)
        # self.queue.mutex.release()
        return frame
    
    def __next__(self):
        """Get next frame of audio packets from queue given frame size
        
        Returns:
            AudioPacket: Audio packet of size frame_size
        
        Raises:
            StopIteration: If queue is empty or if there is not enough data in queue to read frame_size bytes        
        """
        ret = self.read()
        if ret is None:
            raise StopIteration
        return ret
        
    
    def __iter__(self):
        """Get iterator of audio packets from queue given frame size"""
        return self

    def __len__(self):
        """Get length of queue"""
        return self.queue.qsize()

    def _debug_verify_order(self):
        """Verify that queue is in order (For Debugging only) """
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
        """Play audio buffer (For Debugging only)"""
        with self.queue.mutex:
            packet = reduce(lambda x,y : x+y, self.queue.queue)
            sd.play(np.frombuffer(packet.bytes, dtype=np.int16),16000)