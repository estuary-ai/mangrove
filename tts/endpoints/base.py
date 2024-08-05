from typing import Generator, Dict
from abc import ABCMeta, abstractmethod
from core import AudioPacket

class TTSEndpoint(metaclass=ABCMeta):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def text_to_audio_file(self, text, filepath) -> None:
        raise NotImplementedError()

    @abstractmethod
    def text_to_audio(self, text) -> Generator[AudioPacket, None, None]:
        raise NotImplementedError()
        