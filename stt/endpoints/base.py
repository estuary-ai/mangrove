from queue import Queue, Empty
from abc import ABCMeta, abstractmethod
from core import AudioPacket

class STTEndpoint(metaclass=ABCMeta):
    def __init__(self, **kwargs):
        self.input_queue = Queue()

    def feed(self, audio_packet: AudioPacket):
        self.input_queue.put(audio_packet)

    @abstractmethod
    def get_transcription(self):
        raise NotImplementedError()

    @abstractmethod
    def reset(self):
        raise NotImplementedError()
