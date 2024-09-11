from queue import Queue, Empty
from abc import ABCMeta, abstractmethod
from typing import Optional
from functools import reduce

from core import AudioPacket, TextPacket

class STTEndpoint(metaclass=ABCMeta):
    def __init__(self, **kwargs):
        self.input_queue = Queue()

    def feed(self, audio_packet: AudioPacket) -> None:
        self.input_queue.put(audio_packet)

    def get_buffered_audio_packet(self):
        # unpack as many as possible from queue
        if self.input_queue.qsize() == 0:
            return None
        
        while self.input_queue.qsize() > 0:
            audio_packets = []
            while True:
                try:
                    audio_packet = self.input_queue.get_nowait()
                    audio_packets.append(audio_packet)
                except Empty:
                    break

        audio_packet: AudioPacket = reduce(lambda x, y: x + y, audio_packets)
        return audio_packet

    @abstractmethod
    def get_transcription_if_any(self) -> Optional[TextPacket]: # TODO make it a generator and adjust STTController
        raise NotImplementedError()

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError()
