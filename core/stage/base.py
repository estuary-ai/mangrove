from abc import ABCMeta, abstractmethod
from typing import Callable
from threading import RLock
from multiprocessing import JoinableQueue
from loguru import logger
from ..data.data_packet import DataPacket

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server import DigitalAssistant

class PipelineStage(metaclass=ABCMeta):

    input_type = None
    output_type = None

    def __init_subclass__(cls):
        if not any("input_type" in base.__dict__ for base in cls.__mro__ if base is not PipelineStage):
            raise NotImplementedError(
                f"Attribute 'input_type' has not been overwritten in class '{cls.__name__}'"
            )
        # ensure that input_type is not None
        if cls.input_type is None:
            raise NotImplementedError(
                f"Attribute 'input_type' has not been set in class '{cls.__name__}'"
            )

        # same for output_type
        if not any("output_type" in base.__dict__ for base in cls.__mro__ if base is not PipelineStage):
            raise NotImplementedError(
                f"Attribute 'output_type' has not been overwritten in class '{cls.__name__}'"
            )

        if cls.output_type is None:
            raise NotImplementedError(
                f"Attribute 'output_type' has not been set in class '{cls.__name__}'"
            )

    def __init__(
        self,
        verbose=False,
        **kwargs
    ):
        self._input_buffer = JoinableQueue()
        self._verbose = verbose
        self._lock = RLock() # TODO option to disable lock
        self._on_ready_callback = lambda x: None
        self._host: 'DigitalAssistant' = None

    @property
    def host(self):
        return self._host

    @property
    def on_ready_callback(self):
        return self._on_ready_callback

    @on_ready_callback.setter
    def on_ready_callback(self, callback):
        if not isinstance(callback, Callable):
            raise ValueError("Callback must be callable")
        self._on_ready_callback = callback

    @abstractmethod
    def _unpack(self):
        raise NotImplementedError()

    @abstractmethod
    def _process(self, data_packet: DataPacket):
        raise NotImplementedError()

    def on_sleep(self):
        pass

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_start(self):
        pass

    def on_ready(self, inference):
        self.on_ready_callback(inference)

    def start(self, host):
        """Start processing thread"""
        logger.info(f'Starting {self}')

        self._host = host

        self.on_start()

        def _start_thread():
            while True:
                with self._lock:
                    data = self._unpack()
                    data_packet = self._process(data)
                if data_packet is None:
                    self._host.sleep(0.05)
                    self.on_sleep()
                elif not isinstance(data_packet, bool):
                    # TODO this is just hacky way.. use proper standards
                    self.on_ready(data_packet)

        self._processor = self._host.start_background_task(_start_thread)

    def feed(self, data_packet: DataPacket):
        self._input_buffer.put(data_packet)

    def log(self, msg, end="", force=False):
        """Log message to console if verbose is True or force is True with flush

        Args:
            msg (str): Message to log
            end (str, optional): End character. Defaults to "".
            force (bool, optional): Force logging. Defaults to False.

        """
        if self._verbose or force:
            print(msg, end=end, flush=True)