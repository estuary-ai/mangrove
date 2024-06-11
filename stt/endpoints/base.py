from queue import Queue, Empty
from abc import ABCMeta, abstractmethod
from core import AudioPacket

class STTEndpoint(metaclass=ABCMeta):
    def __init__(self, **kwargs):
        self.input_queue = Queue()

    def buffer_audio_packet(self, audio_packet: AudioPacket):
        self.input_queue.put(audio_packet)

    @abstractmethod
    def create_stream(self):
        raise NotImplementedError()

    @abstractmethod
    def get_transcription(self):
        raise NotImplementedError()

    @abstractmethod
    def reset(self):
        raise NotImplementedError()
