from abc import ABCMeta, abstractmethod
from queue import Empty
from functools import reduce
from ..data.audio_packet import AudioPacket
from ..data.audio_buffer import AudioBuffer
from .base import PipelineStage

class AudioToTextStage(PipelineStage, metaclass=ABCMeta):
    def __init__(self, frame_size=512*4, **kwargs):
        super().__init__(**kwargs)
        self._frame_size = frame_size
        self._input_buffer = AudioBuffer(self._frame_size)

    @property
    def input_type(self):
        return AudioPacket

    @property
    def frame_size(self):
        return self._frame_size

    @abstractmethod
    def _process(self, audio_packet: AudioPacket):
        raise NotImplementedError()

    def _unpack(self):
        """Unpack audio packets from input buffer"""
        audio_packets = []
        while True:
            try:
                audio_packet = self._input_buffer.get_no_wait()
                audio_packets.append(audio_packet)
            except AudioBuffer.Empty:
                if len(audio_packets) == 0:
                    # logger.warning('No audio packets found in buffer', flush=True)
                    return
                break

        # NOTE: all packets that were able to get are combined in one here!
        return reduce(lambda x, y: x + y, audio_packets)
