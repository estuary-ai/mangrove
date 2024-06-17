from abc import ABCMeta, abstractmethod
from queue import Empty
from functools import reduce
from ..data.text_packet import TextPacket
from .base import PipelineStage

class TextToTextStage(PipelineStage, metaclass=ABCMeta):

    input_type = TextPacket
    output_type = TextPacket

    @abstractmethod
    def _process(self, text_packet: TextPacket):
        raise NotImplementedError()

    def _unpack(self):
        """Unpack text packets from input buffer"""
        text_packets = []
        try:
            while True:
                text_packet = self._input_buffer.get_nowait()
                assert text_packet is not None
                text_packets.append(text_packet)
        except Empty:
            pass
        if len(text_packets) == 0:
            return None
        return reduce(lambda x, y: x + y, text_packets)
