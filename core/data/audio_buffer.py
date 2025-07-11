import numpy as np
import sounddevice as sd
from functools import reduce
from queue import (
    PriorityQueue, 
    Queue,
)
from core.utils import logger
from .audio_packet import AudioPacket
from .base_data_buffer import BaseDataBuffer, DataBufferEmpty, DataBufferFull


class AudioBuffer(BaseDataBuffer):
    """Data buffer for audio packets"""

    def __init__(self, frame_size=320, max_queue_size=0):
        """Initialize data buffer

        Args:
            frame_size (int, optional): Number of bytes to read from queue. Defaults to 320.
            max_queue_size (int, optional): Maximum number of audio packets to store in queue. Defaults to 100.
        """
        self.max_queue_size = max_queue_size
        self.queue = PriorityQueue(maxsize=self.max_queue_size)
        # self.queue_reception = PriorityQueue(maxsize=self.max_queue_size)
        self.leftover = None
        self.default_frame_size = frame_size
        self.queue_before_reset = None
        self._len = 0

    def set_frame_size(self, frame_size: int) -> None:
        """Set frame size for audio packets

        Args:
            frame_size (int): Number of bytes to read from queue
        """
        self.default_frame_size = frame_size

    def reset(self) -> None:
        """Reset queue to empty state"""
        with self.queue.mutex:
            self.queue_before_reset = self.queue.queue
        self.queue = PriorityQueue(maxsize=self.max_queue_size)

    def __str__(self):
        return " ".join([str(packet) for packet in self.queue.queue])
    
    # def __len__(self) -> int:
    #     """Get length of queue"""
    #     return self._len
    
    def qsize(self) -> int:
        """Get size of queue"""
        return self._len
    
    def full(self) -> bool:
        """Check if queue is full"""
        return self.queue.full()

    def put(self, audio_packet: AudioPacket, timeout=None) -> None:
        """Add audio packet to queue

        Args:
            audio_packet (AudioPacket): Audio packet to add to queue
            timeout (float, optional): Timeout for adding data to queue. Defaults to None, which means no timeout.
        Raises:
            DataBufferFull: If queue is full and timeout is reached
        """
        try:
            # self._len += len(audio_packet)/self.default_frame_size
            self._len += len(audio_packet)
            self.queue.put(audio_packet, timeout=timeout)
        except DataBufferFull:
            raise DataBufferFull

    def get_nowait(self, frame_size=None) -> AudioPacket:
        """Get next frame of audio packets from queue given frame size

        Args:
            frame_size (int, optional): Number of bytes to read from queue. Defaults to self.default_frame_size.

        Returns:
            AudioPacket: Audio packet of size frame_size

        Raises:
            StopIteration: If queue is empty or if there is not enough data in queue to read frame_size bytes
        """
        return self.get(frame_size, timeout=-1)

    def get(self, frame_size=None, timeout=None) -> AudioPacket:
        """Get next frame of audio packets from queue given frame size

        Args:
            frame_size (int, optional): Number of bytes to read from queue. Defaults to self.default_frame_size.
            timeout (float, optional): Timeout for getting data from queue. Defaults to None, which means no timeout.

        Returns:
            AudioPacket: Audio packet of size frame_size

        Raises:
            StopIteration: If queue is empty or if there is not enough data in queue to read frame_size bytes
        """

        frame_size = frame_size or self.default_frame_size
        chunk_len = 0
        data_packets = Queue()  # Maybe not necessary
        if self.leftover is not None:
            data_packets.put_nowait(self.leftover)
            chunk_len += len(self.leftover)
            self._len -= len(self.leftover)

        while chunk_len < frame_size:
            try:
                if timeout == -1:
                    new_packet = self.queue.get_nowait()
                else:
                    new_packet = self.queue.get(timeout=timeout)
                # if resample is not None:
                #     new_packet = new_packet.resample(resample)
            except DataBufferEmpty:
                # if len(data_packets) == 0:
                if data_packets.qsize() == 0:
                    if timeout != -1:
                        logger.warning("AudioBuffer Queue is empty")
                    raise DataBufferEmpty
                else:
                    break
            data_packets.put_nowait(new_packet)
            chunk_len += len(new_packet)
            self._len -= len(new_packet)

        _data_packet_list = []
        while True:
            try:
                _data_packet_list.append(data_packets.get_nowait())
            except DataBufferEmpty:
                break

        if len(_data_packet_list) == 0:
            raise DataBufferEmpty

        data = reduce(lambda x, y: x + y, _data_packet_list)
        frame, leftover = data[:frame_size], data[frame_size:]

        if len(leftover) > 0:
            self.leftover = leftover
            self._len += len(leftover)
        else:
            self.leftover = None

        return frame

    def __next__(self) -> AudioPacket:
        """Get next frame of audio packets from queue given frame size

        Returns:
            AudioPacket: Audio packet of size frame_size

        Raises:
            StopIteration: If queue is empty or if there is not enough data in queue to read frame_size bytes
        """
        try:
            ret = self.get(timeout=-1)
            # if ret is None:
            #     raise StopIteration
        except:
            raise StopIteration
        return ret

    def __iter__(self) -> 'AudioBuffer':
        """Get iterator of audio packets from queue given frame size"""
        return self

    def size_of_leftover(self) -> int:
        """Get length of queue"""
        return self._len

    def _debug_verify_order(self) -> None:
        """Verify that queue is in order (For Debugging only)"""
        with self.queue.mutex:
            # noise_fstamps = []
            # noise_estamps = []
            for i in range(self.queue.qsize - 1):
                try:
                    assert self.queue.queue[i] > self.queue.queue[i + 1]
                except:
                    try:
                        assert (
                            self.queue.queue[i].timestamp
                            == self.queue.queue[i + 1].timestamp
                        )
                        print(f"same {i} == {i+1}")
                    except:
                        print(f"error at {i}, and {i+1}")

    def _debug_play_buffer(self) -> None:
        """Play audio buffer (For Debugging only)"""
        with self.queue.mutex:
            packet = reduce(lambda x, y: x + y, self.queue.queue)
            sd.play(np.frombuffer(packet.bytes, dtype=np.int16), 16000)

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.qsize() == 0 and self.leftover is None

    def dump_to_packet(self) -> AudioPacket:
        """Dump audio buffer to audio packet"""
        data_packets = Queue()
        while not self.is_empty():
            try:
                data_packets.put_nowait(self.get(frame_size=-1))
            except DataBufferEmpty:
                break
        data_packets = [data_packets.get_nowait() for _ in range(data_packets.qsize())]
        data = reduce(lambda x, y: x + y, data_packets)
        return data