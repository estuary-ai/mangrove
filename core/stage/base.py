from abc import ABCMeta, abstractmethod
from typing import Callable, List, Union, Iterator
from threading import Lock

from core.utils import logger
from core.data import DataBuffer, DataBufferEmpty, DataPacket, DataPacketStream, AnyData
from core.data.base_data_buffer import BaseDataBuffer
from core.context import OutcomingStreamContext, IncomingPacketWhileProcessingException

from ..data.exceptions import SequenceMismatchException

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from host import HostNamespace

class PipelineStage(metaclass=ABCMeta):

    input_type = None
    output_type = None

    def __init_subclass__(cls):
        if not any("input_type" in base.__dict__ for base in cls.__mro__ if base is not PipelineStage):
            raise NotImplementedError(
                f"Attribute 'input_type' has not been overwritten in class '{cls.__name__}'"
            )

        if not issubclass(cls.input_type, DataPacket):
            raise TypeError(
                f"Attribute 'input_type' should be a subclass of DataPacket, got {cls.input_type}"
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
        name: str,
        verbose=False,
        **kwargs
    ):
        self._intermediate_input_buffer = []
        self._input_buffer: DataBuffer = None # Assigned based on the previous stage in the pipeline
        self._offloading_buffer: DataBuffer = DataBuffer()  # Buffer for offloading data packets to be processed in a separate thread then sent off to output buffer
        self._output_buffer: DataBuffer = DataBuffer()  # Output buffer for the next stage in the pipeline
        
        self._name = name
        self._verbose = verbose
        self.__lock__ = Lock() # TODO option to disable lock
        self._on_ready_callback = lambda x: None
        self._host: 'HostNamespace' = None
        self._is_interrupt_forward_pending: bool = False
        self._is_interrupt_signal_pending: bool = False

    @property
    def name(self) -> str:
        """Name of the stage"""
        return self._name

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
            # logger.debug("Intermediate buffer is not empty, skipping first get from input buffer")
            pass
            
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
    
    def pack(self, data: Union[DataPacket, Iterator[DataPacket]]) -> None:
        """Queue data to an offloading buffer to (processing can be done in a separate thread), then it will be on output buffer"""
        # if not isinstance(data_packet, self.output_type):
        #     raise ValueError(f"Expected {self.output_type}, got {type(data_packet)}")
        if isinstance(data, Iterator):
            # if data is an iterator, we need to convert it to a DataPacketStream
            data = DataPacketStream(data, source=self.name)
        else:
            assert data.source is None, f"DataPacket source should be None, got {data.source} at {self.__class__.__name__}"
            data.source = self.name  # Set the source of the data packet to the stage name

        if self._offloading_buffer.full():
            raise NotImplementedError(
                f"Offloading buffer is full for {self.__class__.__name__}, cannot pack data: {data}. Consider increasing the buffer size or processing speed."
            )
        self._offloading_buffer.put(data)  # Offload the data packet to the output buffer
        # We mark the complete data packet at the context of the stage as under digestion
        logger.debug(f"Packed data into offloading buffer for {self.__class__.__name__}: {data}")
        from ..context import Context
        Context().record_data_pack(data)
        logger.debug(f"Recorded data packet in context for {self.__class__.__name__}: {data}")

    def start(self, host):
        """Start processing thread"""
        logger.info(f'Starting {self}')

        self._host = host

        self.on_start()

        def _producer_thread():
            while True:
                data = self.unpack() # blocking call: unpacking data from the previous output buffer (input buffer)
                assert data is not None, f"Unpacked data is None at {self.__class__.__name__}, this should not happen"

                assert isinstance(data, DataPacket), f"Expected DataPacket at {self.__class__.__name__}, got {type(data)}"
                # NOTE: start producing task for the stage TODO rename
                with self.__lock__:
                    self.process(data)
                    
                # TODO rethink the interrupt handling
                # if self._is_interrupt_signal_pending:
                #     logger.warning(f"Interrupt signal pending in {self.__class__.__name__}, calling on_interrupt")
                #     self.on_interrupt()
            logger.debug(f"Producer thread for {self.__class__.__name__} stopped")

        def _consumer_thread():
            def _postprocess(packet: DataPacket):
                assert isinstance(packet, DataPacket), f"Expected DataPacket at {self.__class__.__name__}, got {type(packet)}"
                with self.__lock__:
                    self.on_ready_callback(packet)
                    self._output_buffer.put(packet)

            while True:
                logger.debug(f"Waiting for data in offloading buffer at {self.__class__.__name__}")
                data = self._offloading_buffer.get()  # blocking call
                logger.debug(f"Received data from offloading buffer at {self.__class__.__name__}: {data}")
                if isinstance(data, DataPacketStream):
                    logger.debug(f"Processing DataPacketStream at {self.__class__.__name__}: {data}")
                    _current_packet = None
                    while True:
                        try:
                            if _current_packet is not None:
                                # If we have a current packet, we need to post-process it before processing the next one
                                _postprocess(_current_packet)
                                _current_packet = None
                            with OutcomingStreamContext(data) as stream_context:
                                for packet in data: # TODO they are being processed right here
                                    _current_packet = packet
                                    stream_context.raise_error_if_any()
                                    _postprocess(packet)
                            break
                            logger.debug(f"Stream processed successfully at {self.__class__.__name__}")
                        except IncomingPacketWhileProcessingException as e:
                            invalidated = self._on_incoming_packet_while_processing(e, data)
                            if invalidated:
                                logger.warning(f"Invalidating timestamp exception in {self.__class__.__name__}: {e}")
                                # If the stream is invalidated, we skip processing it
                                break
                            else:
                                logger.warning(f"Incoming packet while processing in {self.__class__.__name__}: {e}, but stream is not invalidated, continuing processing")
                                # we are good to go, continue processing the stream
                                pass
                    logger.debug(f"Processed DataPacketStream at {self.__class__.__name__}")
                else:
                    _postprocess(data)

            logger.debug(f"Consumer thread for {self.__class__.__name__} stopped")

        self._producer = self._host.start_background_task(_producer_thread)
        self._consumer = self._host.start_background_task(_consumer_thread)

    def _on_incoming_packet_while_processing(self, exception: IncomingPacketWhileProcessingException, data: AnyData) -> bool:
        """Internal method to handle incoming packet while processing
        This method is called when an incoming packet is received while the stage is processing a data packet or stream.
        It calls the on_incoming_packet_while_processing method, which should be overridden in subclasses to implement specific logic for handling incoming packets while processing.
        If the stream is invalidated, it should return True, otherwise it should return False.
        Args:
            exception (IncomingPacketWhileProcessingException): Exception that contains the incoming (possibly invalidating) record.
            data (AnyData): The data packet or stream that is being processed when the exception occurred.
        Returns:
            bool: True if the stream was invalidated, False otherwise
        """
        if self.on_incoming_packet_while_processing_callback is None:
            self.on_incoming_packet_while_processing_callback(exception, data)
        is_invalidated: bool = self.on_incoming_packet_while_processing(exception, data)
        if is_invalidated:
            if self.on_invalidated_packet_callback is not None:
                self.on_invalidated_packet_callback(exception=exception, invalid_data=data, dst_stage=self)
    
    def on_interrupt(self, timestamp: int) -> None:
        """Handle interrupt signal
        This method is called when an interrupt signal is received. It can be used to handle the interrupt signal, such as stopping the processing of the current data packet or stream.
        The default implementation does nothing, but it can be overridden in subclasses to implement specific logic for handling interrupts.
        
        Args:
            timestamp (int): Timestamp of the interrupt signal
        """
        pass  # Default implementation does nothing

    def on_incoming_packet_while_processing(self, exception: IncomingPacketWhileProcessingException, data: AnyData) -> bool:
        """Handle incoming packet while processing
        This method is called when an incoming packet is received while the stage is processing a data packet or stream.
        It can be used to invalidate the current stream or data packet being processed, and to handle the incoming packet accordingly.
        This method should be overridden in subclasses to implement specific logic for handling incoming packets while processing.
        If the stream is invalidated, it should return True, otherwise it should return False.

        Args:
            exception (IncomingPacketWhileProcessingException): Exception that contains the incoming (possibly invalidating) record.
            data (AnyData): The data packet or stream that is being processed when the exception occurred.

        Returns:
            bool: True if the stream was invalidated, False otherwise
        """
        assert data.timestamp < exception.timestamp, f"Invalidating timestamp should be greater than or equal to the text packet timestamp {data.timestamp}, got {exception.timestamp}"
        return False  # Default behavior is to not invalidate the stream

    @property
    def on_incoming_packet_while_processing_callback(self) -> Callable:
        """Callback to handle incoming packet while processing"""
        return self._on_incoming_packet_while_processing_callback
    
    @on_incoming_packet_while_processing_callback.setter
    def on_incoming_packet_while_processing_callback(self, callback: Callable) -> None:
        """Set the callback to handle incoming packet while processing"""
        if not callable(callback):
            raise ValueError("Callback must be callable")
        self._on_incoming_packet_while_processing_callback = callback

    @property
    def on_invalidated_packet_callback(self) -> Callable:
        """Callback to handle invalidated data packet"""
        return self._on_invalidated_packet_callback
    
    @on_invalidated_packet_callback.setter
    def on_invalidated_packet_callback(self, callback: Callable) -> None:
        """Set the callback to handle invalidated data packet"""
        if not callable(callback):
            raise ValueError("Callback must be callable")
        self._on_invalidated_packet_callback = callback

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

    # def is_interrupt_forward_pending(self):
    #     return self._is_interrupt_forward_pending

    # def schedule_forward_interrupt(self):
    #     self._is_interrupt_forward_pending = True

    # def acknowledge_interrupt_forwarded(self):
    #     self._is_interrupt_forward_pending = False

    # def signal_interrupt(self, timestamp: int):
    #     self._is_interrupt_signal_pending = True
    #     # TODO use timestamp

    # def on_interrupt(self):
    #     pass
        # self._is_interrupt_signal_pending = False
        # self.schedule_forward_interrupt()

    # def invoke_wait_for_incoming_packets_logic(self) -> bool:
    #     """Invoke wait for incoming packets
        
    #     This method is overridden in the stages that need to implement logic to adjust to too slow incoming inputs which has a behavior similar to interruption logic. 

    #     It is called by the orchestrator when it detects through a context manager that the stage is about send off an output packet too soon, and it needs to wait for more input packets to be processed before sending off the output packet. This particularly called when the on_ready_callback is invoked by the processer thread of the stage.

    #     The default logic is to do nothing, but it can be overridden in the subclasses to implement specific logic, such as waiting for more input packets or adjusting the output packet generation logic.

    #     Returns:
    #         bool: True if the stage is waiting for incoming packets, False otherwise.
    #     """
    #     return False