import threading
from typing import Union, Optional, List, Any, TYPE_CHECKING
from abc import ABCMeta
from collections import deque
from core.utils import logger
from core.data import DataPacket, DataPacketStream, AnyData

if TYPE_CHECKING:
    from core.stage import PipelineStage


class SingletonMeta(ABCMeta, type):
    """
    A metaclass for creating singleton classes.
    Ensures that only one instance of the class can be created.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
    
class Context(metaclass=SingletonMeta):
    """
    Context for the pipeline sequence, used to store shared data and state across stages
    useful to manage signals on when a stage has just processed a complete packet,
    this way later stages can react to it if needed.
    An example of this is when VAD just processed a full utterance, and a later stage in the pipeline is still processing the previous utterance, the later stage can be notified to stop processing the previous utterance and wait for processing a combination of the previous and current utterance for more meaningful results.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._incoming_packets_records: deque[DataPacket] = deque(maxlen=50)  # Store the last 50 records
        self._observers: List['OutcomingStreamContext'] = [] 
        
    def record_data_pack(self, data: AnyData) -> None:
        """
        Record a data packet or stream in the context.
        This method is used to store the data packet or stream in the context.

        Args:
            data (AnyData): The data packet or stream to record.
        """
        with self._lock:
            self._incoming_packets_records.append(data)
            self._notify_observers(data)
            logger.debug(f"Recorded data packet/stream: {data}")

    def get_most_recent_data_pack_record(self) -> Optional[AnyData]:
        """
        Get the most recent data packet or stream recorded in the context.
        This method is used to retrieve the most recent data packet or stream recorded in the context.

        Returns:
            Optional[AnyData]: The most recent data packet or stream, or None if no records exist.
        """
        with self._lock:
            if self._incoming_packets_records: # TODO note this for now can be from the future (for instance, pack from a follow up stream rather than the past (which we actually want))
                return self._incoming_packets_records[-1]  # Return the last recorded data packet/stream
            return None
        
    def register_observer(self, observer: 'OutcomingStreamContext') -> None:
        """
        Register an observer to be notified of incoming packets.
        This method is used to register an observer that will be notified when a new data packet or stream is recorded.

        Args:
            observer (OutcomingStreamContext): The observer to register.
        """
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)

    def unregister_observer(self, observer: 'OutcomingStreamContext') -> None:
        """
        Unregister an observer from being notified of incoming packets.
        This method is used to unregister an observer that will no longer be notified when a new data packet or stream is recorded.

        Args:
            observer (OutcomingStreamContext): The observer to unregister.
        """
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)

    def _notify_observers(self, data: AnyData) -> None:
        """
        Notify all registered observers of a new incoming packet.
        This method is used to notify all registered observers that a new data packet or stream has been recorded.

        Args:
            data (AnyData): The data packet or stream to notify observers about.
        """
        for observer in list(self._observers):
            observer.notify_on_new_record_event(data)
            logger.debug(f"Notified observer: {observer} with data: {data}")


class IncomingPacketWhileProcessingException(Exception):
    """Exception raised when an incoming packet is received while the context is processing a block of code."""
    def __init__(self, incoming_packet: AnyData):
        """
        Args:
            incoming_packet (AnyData): The incoming packet that caused the exception.
        """
        super().__init__(f"Incoming packet detected while processing: {incoming_packet}")
        self.incoming_packet = incoming_packet
    
    @property
    def timestamp(self) -> float:
        """
        Returns the timestamp of the incoming packet that caused the exception.
        """
        return self.incoming_packet.timestamp
    
    def __str__(self):
        return f"IncomingPacketWhileProcessingException: {self.incoming_packet} at {self.timestamp} ms"

class OutcomingStreamContext:

    def __init__(self, data: AnyData):
        # Use an Event to signal a change in the variable.
        self._origin_data = data
        self._origin_source = data.source # TODO add source attribute to DataPacket
        self._new_record_event = threading.Event()
        self._monitoring_thread = None
        self.__lock__ = threading.Lock()

    def notify_on_new_record_event(self, record: AnyData) -> None:
        """
        Set the event to signal that the variable has changed.
        This method should be called when the variable is changed.
        """
        with self.__lock__:
            if self._origin_data.timestamp < record.timestamp and \
                record.source != self._origin_source:
                # If the originating timestamp is less than the new record's timestamp,
                # it means that some incoming input was received while processing the block of code.
                self._new_record_event.set()
                logger.warning(f"StreamContextManager: Monitored variable was changed due to src {record.source} at {record.timestamp} ms, which is after originating timestamp: {self._origin_data.timestamp} ms from {self._origin_data}")

    # def _monitor_variable(self):
    #     """
    #     Thread function that waits for the event to be set.
    #     """
    #     # Wait until the event is set (signaling the variable changed).
    #     self._new_record_event.wait()
    #     # Once the event is set, we can check the conditions.

    def raise_error_if_any(self):
        """ Checks if the event is set and raises an exception if it is.
        This method should be called at the end of the context block to ensure that no incoming packets were received while processing.
        As well as, before processing any new data packet or stream.
        If the event is set, it raises an IncomingPacketWhileProcessingException with the invalidating record.
        Raises:
            IncomingPacketWhileProcessingException: If the event is set, indicating that an incoming packet was received while processing.
        """

        with self.__lock__:
            if self._new_record_event.is_set():
                raise IncomingPacketWhileProcessingException(Context().get_most_recent_data_pack_record())

    def __enter__(self):
        # """
        # Starts the monitoring thread.
        # """
        # self._monitoring_thread = threading.Thread(target=self._monitor_variable)
        # self._monitoring_thread.start()
        Context().register_observer(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Checks if the event was set when exiting the context.
        If the event is set, it raises an error.
        If an exception occurred, it returns False to propagate the exception.

        """
        Context().unregister_observer(self)
        self.raise_error_if_any()
        # Return False to propagate other exceptions.
        return False