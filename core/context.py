import threading
from typing import Union, Optional, List, Any
from abc import ABCMeta
from core.utils import logger
from core.data import DataPacket, DataPacketStream
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
        self._data = {}
        self._lock = threading.Lock()
        self._invalidating_timestamps: List[float] = []  # Store timestamps in milliseconds
        self._invalidating_timestamps_event = threading.Event()
        self._source_of_invalidation: List[Union[DataPacket, DataPacketStream]] = []  # Store the source of invalidation

    def record_invalidating_timestamp(self, data: Union[DataPacket, DataPacketStream]) -> None:
        """
        Record the current timestamp to invalidate any data that was set before this timestamp.
        This is useful to ensure that only the most recent data is considered valid.
        """
        with self._lock:
            self._invalidating_timestamps.append(data.timestamp)  # Store timestamp in milliseconds
            self._source_of_invalidation.append(data)
            self._invalidating_timestamps_event.set()  # Signal that a new timestamp has been recorded
            logger.debug(f"Invalidating timestamp recorded: {self._invalidating_timestamps[-1]} ms")
    
    @property
    def invalidating_timestamps_event(self) -> threading.Event:
        """
        Returns the event that signals when a new invalidating timestamp has been recorded.
        This can be used to wait for the next invalidation.
        """
        return self._invalidating_timestamps_event
    
    def get_last_invalidating_timestamp(self) -> Optional[float]:
        """
        Get the last recorded invalidating timestamp.
        Returns:
            float: The last invalidating timestamp in milliseconds, or None if no timestamps have been recorded.
        """
        with self._lock:
            if self._invalidating_timestamps:
                return self._invalidating_timestamps[-1]
            return None
        
    def get_source_of_invalidation(self) -> Optional[Union[DataPacket, DataPacketStream]]:
        """
        Get the source of the last invalidating timestamp.
        Returns:
            Union[DataPacket, DataPacketStream]: The source of the last invalidating timestamp, or None if no timestamps have been recorded.
        """
        with self._lock:
            if self._source_of_invalidation:
                return self._source_of_invalidation[-1]
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if self._data.get(key) is None:
                self._data[key] = []
            self._data[key].append(value)

    def get(self, key: str, default=None) -> List[Any]:
        with self._lock:
            _out = self._data.get(key)
            if _out is None:
                if default is not None:
                    return default
                raise KeyError(f"Key '{key}' not found in context")
            return _out

    def clear(self):
        with self._lock:
            self._data.clear()

class InvalidatingTimestampsException(Exception):
    """Custom exception raised when the monitored variable is changed."""
    def __init__(self, timestamp: float):
        super().__init__(f"Monitored variable was changed at {timestamp} during the context block. This is not allowed.")
        self.timestamp = timestamp

class OutcomingStreamContext:
    """ A context manager that monitors a variable for changes in a separate thread.
    This context manager can be used to ensure that a variable is not changed by another thread
    while a block of code is being executed. If the variable is changed, it raises an error.
    So that the associated logic is to-be-handled by the user of this context manager.
    """
    def __init__(self, data: Union[DataPacket, DataPacketStream], source: PipelineStage):
        # Use an Event to signal a change in the variable.
        self._monitoring_thread = None
        self._invalidating_timestamps_event = Context().invalidating_timestamps_event
        self._is_event_set = threading.Event() # copy that does not get reset
        self._originating_timestamp = data.timestamp
        self._originating_data = data 
        self._src = source  

    def _monitor_variable(self):
        """
        Thread function that waits for the event to be set.
        """
        # Wait until the event is set (signaling the variable changed).
        self._invalidating_timestamps_event.wait()
        # Once the event is set, we can check if the variable has changed.
        self._is_event_set.set()  # Set the event to indicate that the variable has changed.

    def raise_error_if_any(self):
        """Checks if the event was set and raises an error if it was while the conditions are met."""
        if self._is_event_set.is_set():
            # If the event is set, it means the variable was changed while we were in the
            # context manager block.
            last_invalidating_timestamp = Context().get_last_invalidating_timestamp()
            source_of_invalidation: Union[DataPacket, DataPacketStream] = Context().get_source_of_invalidation()
            assert last_invalidating_timestamp is not None, "Last invalidating timestamp should not be None"
            if self._originating_timestamp < last_invalidating_timestamp:
                if hasattr(source_of_invalidation, 'source') and source_of_invalidation.source == self._src.name:
                    return
                logger.warning(f"hasattr(source_of_invalidation, 'source')={hasattr(source_of_invalidation, 'source')}, source_of_invalidation.source={getattr(source_of_invalidation, 'source', None)}")
                logger.warning(f"self._src.name={self._src.name}, source_of_invalidation={source_of_invalidation}")
                # If the originating timestamp is less than the last invalidating timestamp,
                # it means the variable was changed by another thread.
                logger.error(f"StreamContextManager: Monitored variable was changed due to src {source_of_invalidation} at {last_invalidating_timestamp} ms, which is after originating timestamp: {self._originating_timestamp} ms from {self._originating_data}")
                raise InvalidatingTimestampsException(last_invalidating_timestamp)

    def __enter__(self):
        """
        Starts the monitoring thread.
        """
        self._monitoring_thread = threading.Thread(target=self._monitor_variable)
        self._monitoring_thread.start()
        logger.debug("StreamContextManager: Monitoring thread started.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Checks if the event was set when exiting the context.
        If the event is set, it raises an error.
        If an exception occurred, it returns False to propagate the exception.

        """
        self.raise_error_if_any()
        # Return False to propagate other exceptions.
        return False
