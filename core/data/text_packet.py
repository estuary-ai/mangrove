from typing import List
from loguru import logger
from .data_packet import DataPacket


class TextPacket(DataPacket):

    def __init__(
        self, text: str,
        partial: bool, start: bool,
        commands: List[str]=[],
        timestamp=None,
        **metadata # TODO add metadata to all packets
    ):
        super().__init__(timestamp)
        self._text = text
        self.partial = partial
        self.start = start
        self.commands = commands if commands else []
        for key, value in metadata.items():
            setattr(self, key, value)

    @property
    def text(self):
        return self._text

    def to_dict(self):
        return {
            "text": self._text,
            "partial": self.partial,
            "start": self.start,
            "commands": self.commands,
            "timestamp": self.timestamp
        }

    def __str__(self):
        return f"TextPacket({self.timestamp}, {self._text}, {self.partial}, {self.start})"

    def __eq__(self, other):
        return self.timestamp == other.timestamp and self._text == other._text

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __len__(self):
        return len(self._text)

    def __getitem__(self, key):
        return self._text[key]

    def __add__(self, other):
        if self.partial != other.partial and self._timestamp >= 0:
            logger.error(f"Cannot add partial and non-partial packets: {self} + {other}")
            raise ValueError("Cannot add partial and non-partial packets")
        if not self.start and other.start:
            raise ValueError("Cannot add start and non-start packets")

        return TextPacket(
            self._text + other.text,
            self.partial if self._timestamp > -1 else other.partial,
            self.start,
            self.commands + other.commands,
            self._timestamp
        )