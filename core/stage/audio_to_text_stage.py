from typing import Optional
from abc import ABCMeta, abstractmethod
from functools import reduce
from core.data import AudioPacket, TextPacket
from ..data.audio_buffer import AudioBuffer
from .base import PipelineStage

class AudioToTextStage(PipelineStage, metaclass=ABCMeta):

    input_type = AudioPacket
    output_type = TextPacket

    def __init__(self, frame_size=512*4, **kwargs):
        super().__init__(**kwargs)
        self._frame_size = frame_size
        self._input_buffer = AudioBuffer(self._frame_size)

    @property
    def frame_size(self):
        return self._frame_size

    @abstractmethod
    def _process(self, audio_packet: AudioPacket) -> Optional[TextPacket]:
        raise NotImplementedError()