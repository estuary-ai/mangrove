import time
from typing import List
from core.utils import logger
from .data_packet import DataPacket
from .exceptions import SequenceMismatchException

class TextPacket(DataPacket):

    def __init__(
        self, 
        text: str,
        partial: bool,
        start: bool,
        source: str = None,
        commands: List[str]=[],
        timestamp=None,
        **metadata # TODO add metadata to all packets
    ):
        super().__init__(
            source=source,
            timestamp=timestamp,
            start=start,
            partial=partial
        )
        self._text = text
        assert isinstance(self._text, str), f"Text must be a string, got {type(self._text)}"
        self.commands = commands if commands else []
        for key, value in metadata.items():
            setattr(self, key, value)

    @classmethod
    def from_dict(cls, json_data: dict):
        """Create a TextPacket from a dictionary."""
        text = json_data.get("text", "")
        partial = json_data.get("partial", False)
        start = json_data.get("start", True)
        source = json_data.get("source", None)
        commands = json_data.get("commands", [])
        
        return cls(
            text=text,
            partial=partial,
            start=start,
            source=source,
            commands=commands,
        )


    def generate_timestamp(self) -> int:
        """Generate a timestamp in milliseconds."""
        return int(time.time() * 1000)

    @property
    def text(self):
        return self._text

    def to_dict(self):
        return {
            "text": self._text,
            "partial": self._partial,
            "start": self._start,
            "commands": self.commands,
            "timestamp": self.timestamp
        }
    
    @property
    def partial(self):
        return self._partial
    
    @property
    def start(self):
        return self._start

    def __str__(self):
        return f'TextPacket(ts={self.timestamp}, text="{self._text}", partial={self._partial}, start={self._start}, src="{self.source})'

    def __eq__(self, other: 'TextPacket'):
        return self.timestamp == other.timestamp and self._text == other._text

    def __lt__(self, other: 'TextPacket'):
        return self.timestamp < other.timestamp

    def __len__(self):
        return len(self._text)

    def __getitem__(self, key):
        return self._text[key]

    def __add__(self, other: 'TextPacket'):
        if self._partial != other._partial and self._timestamp >= 0:
            raise SequenceMismatchException("Cannot add partial and non-partial packets: {self} + {other}")
        if not self._start and other._start:
            raise SequenceMismatchException("Cannot add start and non-start packets: {self} + {other}")

        return TextPacket(
            text=self._text + other.text,
            partial=self._partial if self._timestamp > -1 else other.partial,
            start=self._start,
            commands=self.commands + other.commands,
            timestamp=self._timestamp
        )