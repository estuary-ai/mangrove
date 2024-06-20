from abc import ABCMeta, abstractmethod
from queue import Empty
from core.data import AudioPacket, TextPacket
from .base import PipelineStage

class TextToAudioStage(PipelineStage, metaclass=ABCMeta):

    input_type = TextPacket
    output_type = AudioPacket

    @abstractmethod
    def _process(self, audio_packet: AudioPacket):
        raise NotImplementedError()

    def _unpack(self):
        try:
            return self._input_buffer.get_nowait()
        except Empty:
            return None