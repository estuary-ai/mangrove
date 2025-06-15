from abc import ABC, ABCMeta
from queue import Empty as DataBufferEmpty
from queue import Full as DataBufferFull

class BaseDataBuffer(ABC, metaclass=ABCMeta):
    """Base class for data buffers.
    This class defines the interface for data buffers, which can be used to store and retrieve data packets.
    It is intended to be subclassed for specific data types.
    """
