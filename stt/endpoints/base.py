from queue import Queue, Empty
from abc import ABCMeta, abstractmethod
from core import AudioPacket, TextPacket

class STTEndpoint(metaclass=ABCMeta):
    def __init__(self, **kwargs):
        self.input_queue = Queue()

    def feed(self, audio_packet: AudioPacket) -> None:
        self.input_queue.put(audio_packet)

    @abstractmethod
    def get_transcription(self) -> TextPacket: # TODO make it a generator and adjust STTController
        raise NotImplementedError()

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError()
