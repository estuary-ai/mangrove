from queue import Queue
from .base_data_buffer import BaseDataBuffer

class DataBuffer(BaseDataBuffer, Queue):
    """Data buffer for any type of data packets."""
    pass