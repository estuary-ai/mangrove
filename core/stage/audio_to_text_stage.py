from typing import Optional
from abc import ABCMeta, abstractmethod
from functools import reduce
from core.data import AudioPacket, TextPacket, AudioBuffer, DataBuffer
from .base import PipelineStage

class AudioToTextStage(PipelineStage, metaclass=ABCMeta):

    input_type = AudioPacket
    output_type = TextPacket

    def __init__(self, name: str, frame_size: int=512*4, **kwargs):
        super().__init__(name=name, **kwargs)
        self._frame_size = frame_size
    
    @property
    def frame_size(self) -> int:
        return self._frame_size

    @abstractmethod
    def process(self, audio_packet: AudioPacket) -> None:
        raise NotImplementedError()