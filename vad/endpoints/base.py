import collections
from typing import Union, List
from abc import ABCMeta, abstractmethod
from functools import reduce
from queue import Queue, Empty
from loguru import logger

from storage_manager import write_output
from core import AudioBuffer, AudioPacket

class VoiceActivityDetector(metaclass=ABCMeta):

    def __init__(
        self, silence_threshold: int = 200, frame_size: int = 320 * 3, verbose=False
    ):
        self.silence_threshold = silence_threshold
        self.frame_size = frame_size

        self.front_silences = collections.deque(maxlen=2)
        self.verbose = verbose
    
        self._is_started = False
        self.num_recorded_chunks = 0
        self.end_silence_timestamp = None
        self._reset_silence_buffer()

        # TODO make them in one debug variable
        self._command_audio_packet = None
        self._output_queue = Queue()


    def _concat_buffered_silence(self, audio_packet: AudioPacket):
        """Concatenate buffered silence to voice frame"""

        if len(self.front_silences) > 0:
            # if there were silence buffers append them
            # DEBUG START
            silence_len = reduce(
                lambda x, y: len(x) + len(y), self.front_silences
            )
            if isinstance(silence_len, AudioPacket):
                silence_len = len(silence_len)

            # DEBUG END
            self.front_silences.append(audio_packet)
            complete_frame = reduce(lambda x, y: x + y, self.front_silences)
            self._reset_silence_buffer()
        else:
            complete_frame = audio_packet
        return complete_frame
    
    def feed(self, audio_packet: AudioPacket) -> None:
        if self.is_speech(audio_packet):
            if self._command_audio_packet is None:
                frame_inc_silence = self._concat_buffered_silence(audio_packet)
                self._command_audio_packet = audio_packet
                logger.success(f"Starting an utterance AudioPacket at {audio_packet.timestamp}")
            else:
                self._command_audio_packet += audio_packet
            
        else:
            # silence    
            if self._command_audio_packet is not None:
                # detected silence after voice
                # append silence to voice
                self._command_audio_packet += audio_packet

                # Check if silence threshold is reached ?? TODO
                if self.end_silence_timestamp is None:
                    self.end_silence_timestamp = audio_packet.timestamp
                else:
                    # TODO test using command_audio_buffer instead
                    now_timestamp = audio_packet.timestamp + audio_packet.duration
                    # TODO should i use now_timestamp or  audio_packet.timestamp
                    silence_duration = now_timestamp - self.end_silence_timestamp
                    # logger.debug(f'Got Silence after voice duration: {silence_duration}')
                    if silence_duration >= self.silence_threshold:
                        self.end_silence_timestamp = None
                        self.log("\n[end]", force=True)
                    
                        self._output_queue.put(self._command_audio_packet)
                        self._command_audio_packet = None
            else:
                self.front_silences.append(audio_packet)
    
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

    def reset(self) -> None:
        assert self._is_started, "Recording not started"
        self._is_started = False

        self.num_recorded_chunks = 0
        self.end_silence_timestamp = None
        self._reset_silence_buffer()

    def _reset_silence_buffer(self) -> None:
        """Reset silence buffer"""
        # TODO try increasing size
        self.front_silences = collections.deque(maxlen=2)
        self.num_recorded_chunks = 0

    @abstractmethod
    def is_speech(self, audio_packets: Union[List[AudioPacket], AudioPacket]) -> Union[bool, List[bool]]:
        raise NotImplementedError("is_speech must be implemented in subclass")

    def log(self, msg, end="", force=False) -> None: # TODO: refactor out into progress logger
        """Log message to console if verbose is True or force is True with flush

        Args:
            msg (str): Message to log
            end (str, optional): End character. Defaults to "".
            force (bool, optional): Force logging. Defaults to False.

        """
        if self.verbose or force:
            write_output(msg, end=end)