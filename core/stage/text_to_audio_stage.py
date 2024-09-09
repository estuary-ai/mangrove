from typing import Optional
from abc import ABCMeta, abstractmethod
from queue import Empty
from core.data import AudioPacket, TextPacket
from .base import PipelineStage

class TextToAudioStage(PipelineStage, metaclass=ABCMeta):

    input_type = TextPacket
    output_type = AudioPacket

    @abstractmethod
    def _process(self, text_packet: TextPacket) -> Optional[AudioPacket]:
        raise NotImplementedError()