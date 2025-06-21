import time
from abc import ABCMeta

class AnyData(metaclass=ABCMeta):

    def __init__(self, source: str = None, timestamp: int = None):
        """Constructor for Data.
        Args:
            source (str, optional): Source of the data. Defaults to None.
        """
        self._source = source
        self._creation_time = int(time.time()* 1000)  # Store creation time in milliseconds
        if timestamp is None:
            try:
                timestamp = self.generate_timestamp()
            except NotImplementedError:
                raise NotImplementedError(
                    f"{self.__class__.__name__} does not implement generate_timestamp method to support automatic timestamp generation."
                )
        self._timestamp = timestamp

    def generate_timestamp(self) -> int:
        raise NotImplementedError("Subclasses must implement generate_timestamp method")

    @property
    def timestamp(self):
        """Get the timestamp of the data packet.
        Returns:
            int: Timestamp in milliseconds.
        """
        return self._timestamp
    
    @property
    def source(self) -> str:
        """Get the source of the data.
        Returns:
            str: Source of the data.
        """
        return self._source
    
    @property
    def creation_time(self) -> int:
        """Get the creation time of the DataPacketStream."""
        return self._creation_time

    @source.setter
    def source(self, value: str):
        """Set the source of the data.
        Args:
            value (str): Source of the data.
        """
        self._source = value