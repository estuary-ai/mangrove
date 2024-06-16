import functools
from typing import Type
from abc import ABCMeta, abstractmethod
from datetime import datetime

@functools.total_ordering
class DataPacket(metaclass=ABCMeta):

    def __init__(self, timestamp=None, **kwargs):
        if timestamp is None:
            timestamp = int(round(datetime.now().timestamp()))
        self._timestamp = timestamp

    @property
    def timestamp(self):
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
