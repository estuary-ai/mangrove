from abc import ABCMeta, abstractmethod
from threading import RLock
from multiprocessing import JoinableQueue
from queue import Empty
from functools import reduce
from .data.data_packet import DataPacket
from .data.audio_packet import AudioPacket
from .data.audio_buffer import AudioBuffer

def _combine_outcomes(outcomes):
    """Combine outcomes of multiple segments into one

    Args:
        outcomes (list): List of outcomes (transcriptions)

    Returns:
        dict: Merged outcome
    """

    def _gen_base_case(value):
        if isinstance(value, str):
            return ""
        elif isinstance(value, bytes):
            return b""
        elif isinstance(value, (float, int)):
            return 0
        elif isinstance(value, dict):
            _base = {}
            for key, value in value.items():
                _base[key] = _gen_base_case(value)
            return _base
        else:
            raise TypeError(f"Unknown type {type(value)}")

    merged_outcome = {
        key: _gen_base_case(value) for key, value in outcomes[0].items()
    }

    for outcome in outcomes:
        for key, value in outcome.items():
            if isinstance(value, str):
                merged_outcome[key] += value.strip()
            elif isinstance(value, dict):
                for _key, _value in value.items():
                    merged_outcome[key][_key] += _value
            else:
                merged_outcome[key] += value
    return merged_outcome

class PipelineStage(metaclass=ABCMeta):
    def __init__(
        self,
        verbose=False,
        **kwargs
    ):
        self._input_buffer = JoinableQueue()
        self._output_buffer = JoinableQueue()
        self._verbose = verbose
        self._lock = RLock() # TODO option to disable lock

    @abstractmethod
    def _unpack(self):
        raise NotImplementedError()

    @abstractmethod
    def _process(self, data_packet: DataPacket):
        raise NotImplementedError()

    def on_sleep(self):
        pass

    def on_start(self):
        pass

    def start(self, server):
        """Start processing thread"""
        print('starting', self)

        self.on_start()

        def _start_thread():
            while True:
                with self._lock:
                    data = self._unpack()
                    inference = self._process(data)
                if inference is None:
                    server.sleep(0.05)
                    self.on_sleep()
                elif not isinstance(inference, bool):
                    # TODO this is just hacky way.. use proper standards
                    self._output_buffer.put(inference)

        self._processor = server.start_background_task(_start_thread)

    def feed(self, data_packet: DataPacket):
        self._input_buffer.put(data_packet)

    def receive(self):
        """Get output"""
        try:
            return self._output_buffer.get_nowait()
        except Empty:
            return None

    def log(self, msg, end="", force=False):
        """Log message to console if verbose is True or force is True with flush

        Args:
            msg (str): Message to log
            end (str, optional): End character. Defaults to "".
            force (bool, optional): Force logging. Defaults to False.

        """
        if self._verbose or force:
            print(msg, end=end, flush=True)


class TextToTextStage(PipelineStage, metaclass=ABCMeta):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def _process(self, text_packet: DataPacket):
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



class AudioToTextStage(PipelineStage, metaclass=ABCMeta):
    def __init__(self, frame_size=512*4, **kwargs):
        super().__init__(**kwargs)
        self._frame_size = frame_size
        self._input_buffer = AudioBuffer(self._frame_size)

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
                audio_packet = self._input_buffer.get(self.frame_size, timeout=-1)
                audio_packets.append(audio_packet)
            except AudioBuffer.Empty:
                if len(audio_packets) == 0:
                    # logger.warning('No audio packets found in buffer', flush=True)
                    return
                break

        # NOTE: all packets that were able to get are combined in one here!
        return reduce(lambda x, y: x + y, audio_packets)
