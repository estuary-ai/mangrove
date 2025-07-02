import time
from typing import Generator, Iterator
from .data_packet import DataPacket
from .any_data import AnyData

# TODO allow annotating it to a particular type of DataPacket
class DataPacketStream(Iterator[DataPacket], AnyData):
    """
    A class to represent a stream of data packets. A wrapper around a generator that yields DataPacket objects.
    """

    def __init__(self, generator: Generator[DataPacket, None, None], source: str):
        """
        Initialize the DataPacketStream with a generator.

        Args:
            generator (Generator[DataPacket, None, None]): A generator that yields DataPacket objects.
        """
        super().__init__(source=source, timestamp=int(time.time() * 1000))  # Store creation time in milliseconds
        self._generator = generator
        self._current_packet = None
    
    def generate_timestamp(self):
        return self.creation_time
    
    def __iter__(self):
        """Return the iterator for the DataPacketStream."""
        return self

    def __next__(self) -> DataPacket:
        """Get the next DataPacket from the stream."""
        self._current_packet = next(self._generator)
        return self._current_packet

    def __str__(self) -> str:
        """String representation of the DataPacketStream."""
        return f"DataPacketStream(timestamp={self._creation_time}, current_packet={self._current_packet}, source={self._source})"
