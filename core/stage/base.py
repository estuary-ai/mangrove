from abc import ABCMeta, abstractmethod
from typing import Callable, List, Optional, Union, Iterator
from threading import Lock

from core.utils import logger
from core.data import DataBuffer, DataBufferEmpty, DataPacket
from core.data.base_data_buffer import BaseDataBuffer
from ..data.exceptions import SequenceMismatchException

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
        self._intermediate_input_buffer = []
        self._input_buffer: DataBuffer = None # Assigned based on the previous stage in the pipeline
        self._offloading_buffer: DataBuffer = DataBuffer()  # Buffer for offloading data packets to be processed in a separate thread then sent off to output buffer
        self._output_buffer: DataBuffer = DataBuffer()  # Output buffer for the next stage in the pipeline

        self._verbose = verbose
        self._lock = Lock() # TODO option to disable lock
        self._on_ready_callback = lambda x: None
        self._host: 'DigitalAssistant' = None
        self._is_interrupt_forward_pending: bool = False
        self._is_interrupt_signal_pending: bool = False

    @property
    def input_buffer(self) -> BaseDataBuffer:
        """Input buffer for the stage"""
        return self._input_buffer
    
    @input_buffer.setter
    def input_buffer(self, buffer: BaseDataBuffer):
        # if not isinstance(buffer, BaseDataBuffer):
        #     raise ValueError(f"Expected BaseDataBuffer, got {type(buffer)}")
        logger.debug(f"Setting input buffer for {self.__class__.__name__} to {buffer}")
        self._input_buffer = buffer

    @property
    def output_buffer(self) -> BaseDataBuffer:
        """Output buffer for the stage"""
        return self._output_buffer
    
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

    def unpack(self) -> DataPacket:
        """Unpack data from input buffer and return a complete DataPacket
        This method collects data packets from the input buffer and combines them into a single DataPacket, that can be processed by the next stage in the pipeline.
        """
        if self._input_buffer is None:
            raise RuntimeError("Input buffer is not set. Please set the input buffer before unpacking data.")
        
        data_packets: List[DataPacket] = self._intermediate_input_buffer
        self._intermediate_input_buffer = []

        if not data_packets:  # if intermediate buffer is empty, we need to get at least one packet from input buffer
            data_packet = self._input_buffer.get()  # blocking call at least for the first time
            data_packets.append(data_packet)
        else:
            logger.debug("Intermediate buffer is not empty, skipping first get from input buffer")

        # Now we have at least one packet in data_packets, we can try to get more packets
        while True:
            try:
                data_packet = self._input_buffer.get_nowait()
                data_packets.append(data_packet)
            except DataBufferEmpty:
                # if len(data_packets) == 0:
                #     # logger.warning('No audio packets found in buffer', flush=True)
                #     return
                break

        complete_data_packet = data_packets[0]
        for i, data_packet in enumerate(data_packets[1:], start=1):
            try:
                complete_data_packet += data_packet
            except SequenceMismatchException as e:
                for j in range(i, len(data_packets)):
                    self._intermediate_input_buffer.append(data_packets[j])
                break
        
        return complete_data_packet
        
    def pack(self, data_packet: Union[DataPacket, Iterator[DataPacket]]) -> None:
        """Queue data packet to an offloading buffer to (processing can be done in a separate thread), then it will be on output buffer"""
        # if not isinstance(data_packet, self.output_type):
        #     raise ValueError(f"Expected {self.output_type}, got {type(data_packet)}")
        if self._offloading_buffer.full():
            logger.warning(f"Output buffer is full, dropping data packet: {data_packet}")
            return
        self._offloading_buffer.put(data_packet)  # Offload the data packet to the output buffer

    def start(self, host):
        """Start processing thread"""
        logger.info(f'Starting {self}')

        self._host = host

        self.on_start()

        def _producer_thread():
            while True:
                # with self._lock:
                data = self.unpack() # blocking call: unpacking data from the previous output buffer (input buffer)
                assert isinstance(data, DataPacket), f"Expected DataPacket at {self.__class__.__name__}, got {type(data)}"
                # NOTE: start producing task for the stage TODO rename
                self.process(data)
                
                # TODO rethink the interrupt handling
                # if self._is_interrupt_signal_pending:
                #     logger.warning(f"Interrupt signal pending in {self.__class__.__name__}, calling on_interrupt")
                #     self.on_interrupt()

        def _consumer_thread():
            def _postprocess(packet: DataPacket):
                assert isinstance(packet, DataPacket), f"Expected DataPacket at {self.__class__.__name__}, got {type(packet)}"
                # TODO: check if data_packet is invalid for some reason!
                self.on_ready_callback(packet)
                self._output_buffer.put(packet)

            while True:
                data_packet = self._offloading_buffer.get()  # blocking call
                if isinstance(data_packet, Iterator):
                    for packet in data_packet: # TODO they are being processed right here
                        _postprocess(packet)
                else:
                    _postprocess(data_packet)

        self._producer = self._host.start_background_task(_producer_thread)
        self._consumer = self._host.start_background_task(_consumer_thread)

    @abstractmethod
    def process(self, data_packet: DataPacket) -> None:
        """Issue processing task for the stage"""
        raise NotImplementedError()

    def on_connect(self) -> None:
        pass

    def on_disconnect(self) -> None:
        pass

    def on_start(self) -> None:
        pass

    def feed(self, data_packet: DataPacket) -> None:
        self._input_buffer.put(data_packet)

    def log(self, msg, end="", force=False) -> None:
        """Log message to console if verbose is True or force is True with flush

        Args:
            msg (str): Message to log
            end (str, optional): End character. Defaults to "".
            force (bool, optional): Force logging. Defaults to False.

        """
        if self._verbose or force:
            print(msg, end=end, flush=True)

    def is_interrupt_forward_pending(self):
        return self._is_interrupt_forward_pending

    def schedule_forward_interrupt(self):
        self._is_interrupt_forward_pending = True

    def acknowledge_interrupt_forwarded(self):
        self._is_interrupt_forward_pending = False

    def signal_interrupt(self, timestamp: int):
        self._is_interrupt_signal_pending = True
        # TODO use timestamp

    def on_interrupt(self):
        self._is_interrupt_signal_pending = False
        self.schedule_forward_interrupt()
