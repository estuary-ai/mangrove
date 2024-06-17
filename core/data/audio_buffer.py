import numpy as np
import sounddevice as sd

from functools import reduce
from queue import PriorityQueue, Queue
from queue import Empty as QueueEmpty
from queue import Full as QueueFull
from loguru import logger
from threading import RLock
from .audio_packet import AudioPacket


class AudioBuffer:
    """Data buffer for audio packets"""

    class Empty(Exception):
        """Exception raised when queue is empty"""

        pass

    class Full(Exception):
        """Exception raised when queue is full"""

        pass

    def __init__(self, frame_size=320, max_queue_size=0):
        """Initialize data buffer

        Args:
            frame_size (int, optional): Number of bytes to read from queue. Defaults to 320.
            max_queue_size (int, optional): Maximum number of audio packets to store in queue. Defaults to 100.
        """
        self.max_queue_size = max_queue_size
        self.queue = PriorityQueue(maxsize=self.max_queue_size)
        self.leftover = None
        self.default_frame_size = frame_size
        self.queue_before_reset = None
        self._len = 0
        self._lock = RLock()

    def reset(self):
        """Reset queue to empty state"""
        with self.queue.mutex:
            self.queue_before_reset = self.queue.queue
        self.queue = PriorityQueue(maxsize=self.max_queue_size)

    def __str__(self):
        return " ".join([str(packet) for packet in self.queue.queue])

    def put(self, audio_packet: AudioPacket, timeout=0.5):
        """Add audio packet to queue

        Args:
            audio_packet (AudioPacket): Audio packet to add to queue
        """
        with self._lock:
            try:
                # self._len += len(audio_packet)/self.default_frame_size
                self._len += len(audio_packet)
                self.queue.put(audio_packet, timeout=timeout)
            except QueueFull:
                raise AudioBuffer.Full

    def get_no_wait(self, frame_size=None):
        """Get next frame of audio packets from queue given frame size

        Args:
            frame_size (int, optional): Number of bytes to read from queue. Defaults to self.default_frame_size.

        Returns:
            AudioPacket: Audio packet of size frame_size

        Raises:
            StopIteration: If queue is empty or if there is not enough data in queue to read frame_size bytes
        """
        with self._lock:
            return self._get(frame_size, timeout=-1)

    def get(self, frame_size=None, timeout=0.5) -> AudioPacket:
        """Get next frame of audio packets from queue given frame size

        Args:
            frame_size (int, optional): Number of bytes to read from queue. Defaults to self.default_frame_size.

        Returns:
            AudioPacket: Audio packet of size frame_size

        Raises:
            StopIteration: If queue is empty or if there is not enough data in queue to read frame_size bytes
        """
        with self._lock:
            return self._get(frame_size, timeout)

    def _get(self, frame_size=None, timeout=0.5):
        """Get next frame of audio packets from queue given frame size

        Args:
            frame_size (int, optional): Number of bytes to read from queue. Defaults to self.default_frame_size.

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
            except QueueEmpty:
                # if len(data_packets) == 0:
                if data_packets.qsize() == 0:
                    if timeout != -1:
                        logger.warning("AudioBuffer Queue is empty")
                    raise AudioBuffer.Empty
                else:
                    break
            data_packets.put_nowait(new_packet)
            chunk_len += len(new_packet)
            self._len -= len(new_packet)

        _data_packet_list = []
        while True:
            try:
                _data_packet_list.append(data_packets.get_nowait())
            except QueueEmpty:
                break

        if len(_data_packet_list) == 0:
            raise AudioBuffer.Empty

        data = reduce(lambda x, y: x + y, _data_packet_list)
        frame, leftover = data[:frame_size], data[frame_size:]

        if len(leftover) > 0:
            self.leftover = leftover
            self._len += len(leftover)
        else:
            self.leftover = None

        return frame

    def __next__(self):
        """Get next frame of audio packets from queue given frame size

        Returns:
            AudioPacket: Audio packet of size frame_size

        Raises:
            StopIteration: If queue is empty or if there is not enough data in queue to read frame_size bytes
        """
        try:
            ret = self.get(timeout=0.1)
            # if ret is None:
            #     raise StopIteration
        except:
            raise StopIteration
        return ret

    def __iter__(self):
        """Get iterator of audio packets from queue given frame size"""
        return self

    def size_of_leftover(self):
        """Get length of queue"""
        return self._len

    def _debug_verify_order(self):
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

    def _debug_play_buffer(self):
        """Play audio buffer (For Debugging only)"""
        with self.queue.mutex:
            packet = reduce(lambda x, y: x + y, self.queue.queue)
            sd.play(np.frombuffer(packet.bytes, dtype=np.int16), 16000)

    def is_empty(self):
        """Check if queue is empty"""
        return self.queue.qsize() == 0 and self.leftover is None


    def dump_to_packet(self):
        """Dump audio buffer to audio packet"""
        with self._lock:
            data_packets = Queue()
            while not self.is_empty():
                try:
                    data_packets.put_nowait(self.get(frame_size=-1))
                except AudioBuffer.Empty:
                    break
            data_packets = [data_packets.get_nowait() for _ in range(data_packets.qsize())]
            data = reduce(lambda x, y: x + y, data_packets)
            return AudioPacket(data)