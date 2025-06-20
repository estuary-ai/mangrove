import time
from typing import Generator, Iterator
from .data_packet import DataPacket

# TODO allow annotating it to a particular type of DataPacket
class DataPacketStream(Iterator[DataPacket]):
    """
    A class to represent a stream of data packets. A wrapper around a generator that yields DataPacket objects.
    """

    def __init__(self, generator: Generator[DataPacket, None, None], source: str):
        """
        Initialize the DataPacketStream with a generator.

        Args:
            generator (Generator[DataPacket, None, None]): A generator that yields DataPacket objects.
        """
        self._creation_time = int(time.time()* 1000)  # Store creation time in milliseconds
        self._generator = generator
        self._current_packet = None
        self._source = source

    @property
    def source(self) -> str:
        """Get the source of the DataPacketStream."""
        return self._source

    @property
    def creation_time(self) -> int:
        """Get the creation time of the DataPacketStream."""
        return self._creation_time
    
    @property
    def timestamp(self) -> int:
        return self._creation_time

    # @property
    # def timestamp(self) -> int:
    #     """Get the timestamp of the DataPacketStream. It is dynamically updated to the timestamp of the current packet."""
    #     if self._current_packet is not None:
    #         return self._current_packet.timestamp
    #     return self._creation_time
    
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
