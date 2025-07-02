from typing import Optional
from abc import ABCMeta, abstractmethod
from queue import Empty
from functools import reduce
from ..data.text_packet import TextPacket
from .base import PipelineStage

class TextToTextStage(PipelineStage, metaclass=ABCMeta):

    input_type = TextPacket
    output_type = TextPacket

    @abstractmethod
    def process(self, text_packet: TextPacket) -> None:
        raise NotImplementedError()