import functools
from typing import Type
from abc import ABCMeta, abstractmethod
from datetime import datetime

@functools.total_ordering
class DataPacket(metaclass=ABCMeta):

    def __init__(
        self, 
        timestamp: int = None,
        start: bool = False,
        partial: bool = False,
        **kwargs
    ):
        """Constructor for DataPacket.
        Args:
            timestamp (int, optional): Timestamp in milliseconds. Defaults to current time in milliseconds.
            start (bool, optional): Indicates if this is the start of a new data packet. Defaults to False.
            partial (bool, optional): Indicates if this is a partial data packet. Defaults to False.
        """
        if timestamp is None:
            try:
                timestamp = self.generate_timestamp()
            except NotImplementedError:
                raise NotImplementedError(
                    f"{self.__class__.__name__} does not implement generate_timestamp method to support automatic timestamp generation."
                )
        self._timestamp = timestamp
        self._start = start
        self._partial = partial

    def generate_timestamp(self) -> int:
        raise NotImplementedError("Subclasses must implement generate_timestamp method")

    @property
    def timestamp(self):
        """Get the timestamp of the data packet.
        Returns:
            int: Timestamp in milliseconds.
        """
        return self._timestamp

    def to_dict(self) -> dict:
        return {"timestamp": self.timestamp}

    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def __eq__(self, __o: object) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def __lt__(self, __o: object) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def __len__(self) -> int:
        raise NotImplementedError()

    @abstractmethod
    def __getitem__(self, key):
        raise NotImplementedError()

    @abstractmethod
    def __add__(self, _data_packet: Type["DataPacket"]):
        raise NotImplementedError()
