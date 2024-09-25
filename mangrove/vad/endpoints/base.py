import collections
from typing import Union, List
from abc import ABCMeta, abstractmethod
from functools import reduce
from queue import Queue, Empty
from loguru import logger

from storage_manager import write_output
from core import AudioBuffer, AudioPacket

class VoiceActivityDetector(metaclass=ABCMeta):

    @abstractmethod
    def is_speech(self, audio_packets: Union[List[AudioPacket], AudioPacket]) -> Union[bool, List[bool]]:
        raise NotImplementedError("is_speech must be implemented in subclass")

    def __init__(
        self, tail_silence_threshold: int = 150, frame_size: int = 320 * 3, verbose=False
    ):
        self._verbose = verbose

        self._tail_silence_threshold = tail_silence_threshold
        self._frame_size = frame_size
    
        self._is_started = False
        self._tail_silence_timestamp = None
        self._reset_head_silences_buffer()

        self._command_audio_packet = None
        self._output_queue = Queue()

    @property
    def frame_size(self):
        return self._frame_size

    def reset(self) -> None:
        assert self._is_started, "Recording not started"
        self._is_started = False
        self._command_audio_packet = None
        self._tail_silence_timestamp = None
        self._reset_head_silences_buffer()

    def _reset_head_silences_buffer(self, amount_to_keep_ms=200) -> None:
        """Reset silence buffer"""
        amount_to_keep_packets = (self._frame_size // 320) * (amount_to_keep_ms // 20)
        self._head_silences_buffer = collections.deque(maxlen=amount_to_keep_packets)
        self._num_recorded_chunks = 0

    def _concat_head_buffered_silences(self, audio_packet: AudioPacket):
        """Concatenate buffered silence to voice frame"""

        if len(self._head_silences_buffer) > 0:
            # if there were silence buffers append them to the voice
            silence_audio_packet: AudioPacket = reduce(lambda x, y: x + y, self._head_silences_buffer)
            complete_frame = silence_audio_packet + audio_packet
            logger.debug(f'Concatenated a duration {silence_audio_packet.duration} silences to voice of duration {audio_packet.duration}')
            self._reset_head_silences_buffer()
        else:
            complete_frame = audio_packet
        return complete_frame
    
    def feed(self, audio_packet: AudioPacket) -> None:
        if self.is_speech(audio_packet):
            if self._command_audio_packet is None:
                self._command_audio_packet = self._concat_head_buffered_silences(audio_packet)
                logger.success(f"Starting an utterance AudioPacket at {self._command_audio_packet.timestamp}")
            else:
                self._command_audio_packet += audio_packet
            
        else:
            # silence    
            if self._command_audio_packet is not None:
                # detected silence after voice
                # append silence to voice
                self._command_audio_packet += audio_packet

                # Check if silence threshold is reached ?? TODO
                if self._tail_silence_timestamp is None:
                    self._tail_silence_timestamp = audio_packet.timestamp
                else:
                    # TODO test using command_audio_buffer instead
                    now_timestamp = audio_packet.timestamp + audio_packet.duration
                    # TODO should i use now_timestamp or  audio_packet.timestamp
                    silence_duration = now_timestamp - self._tail_silence_timestamp
                    # logger.debug(f'Got Silence after voice duration: {silence_duration}')
                    if silence_duration >= self._tail_silence_threshold:
                        self._tail_silence_timestamp = None
                        self.log("\n[end]", force=True)
                    
                        self._output_queue.put(self._command_audio_packet)
                        self._command_audio_packet = None
            else:
                assert isinstance(audio_packet, AudioPacket), f"audio_packet must be AudioPacket, found {type(audio_packet)}"
                self._head_silences_buffer.append(audio_packet)
    
    def get_utterance_if_any(self) -> Union[AudioPacket, None]:
        if self._output_queue.qsize() == 0:
            return None
        audio_packets = []
        while self._output_queue.qsize() > 0:
            audio_packet = self._output_queue.get_nowait()
            audio_packets.append(audio_packet)
        audio_packet: AudioPacket = reduce(lambda x, y: x + y, audio_packets)
        return audio_packet
    
    def is_speaking(self, threshold=500) -> bool:
        return self._command_audio_packet is not None and self._command_audio_packet.duration >= threshold

    def log(self, msg, end="", force=False) -> None: # TODO: refactor out into progress logger
        """Log message to console if verbose is True or force is True with flush

        Args:
            msg (str): Message to log
            end (str, optional): End character. Defaults to "".
            force (bool, optional): Force logging. Defaults to False.

        """
        if self._verbose or force:
            write_output(msg, end=end)