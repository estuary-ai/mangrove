import functools
from typing import Type
from abc import abstractmethod
from copy import deepcopy
from .any_data import AnyData

@functools.total_ordering
class DataPacket(AnyData):

    def __init__(
        self, 
        source: str = None,
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
        super().__init__(source=source, timestamp=timestamp)
        self._start = start
        self._partial = partial

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

    def copy(self) -> "DataPacket":
        """Create a copy of the DataPacket instance.
        Returns:
            DataPacket: A new instance of the same type with the same attributes.
        """
        return deepcopy(self)