from typing import Optional
from abc import ABCMeta, abstractmethod
from functools import reduce
from core.data import AudioPacket, TextPacket
from ..data.audio_buffer import AudioBuffer
from .base import PipelineStage

class AudioToAudioStage(PipelineStage, metaclass=ABCMeta):

    input_type = AudioPacket
    output_type = AudioPacket

    def __init__(self, frame_size=512*4, **kwargs):
        super().__init__(**kwargs)
        self._frame_size = frame_size
        self._output_buffer = AudioBuffer()
        
    @property
    def frame_size(self) -> int:
        return self._frame_size

    @abstractmethod
    def process(self, audio_packet: AudioPacket) -> None:
        raise NotImplementedError()