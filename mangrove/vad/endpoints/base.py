import collections
from typing import Union, List
from abc import ABCMeta, abstractmethod
from functools import reduce
from queue import Queue, Empty

from storage_manager import write_output
from core import AudioBuffer, AudioPacket
from core.utils import logger

class VoiceActivityDetector(metaclass=ABCMeta):

    @abstractmethod
    def is_speech(self, audio_packets: Union[List[AudioPacket], AudioPacket]) -> Union[bool, List[bool]]:
        raise NotImplementedError("is_speech must be implemented in subclass")

    def __init__(
        self,
        head_silence_buffer_size: int = 200, # to buffer some silence at the head of the utterance
        tail_silence_threshold: int = 300, # to cut off the utterance and send it off
        threshold_to_determine_speaking: int = 1000, # 1 second
        frame_size: int = 320 * 3,
        verbose: bool = False
    ):
        """
        Initialize the VoiceActivityDetector.
        
        Args:
            head_silence_buffer_size (int): Amount of buffered silence in milliseconds to place at the head of the utterance.
            tail_silence_threshold (int): Amount of silence in milliseconds after which the utterance is observed before it is sent off.
            threshold_to_determine_speaking (int): Minimum duration in milliseconds of the utterance to be considered as speaking.
            frame_size (int): Size of the audio frame in samples.
            verbose (bool): If True, enables verbose logging.
        """

        self._verbose = verbose

        self._tail_silence_threshold: int = tail_silence_threshold
        self._frame_size: int = frame_size
        self._head_silence_buffer_size: int = head_silence_buffer_size
        self._threshold_to_determine_speaking: int = threshold_to_determine_speaking

        self._tail_silence_start_timestamp: int = None
        self._reset_head_silences_buffer()

        self._command_audio_packet: AudioPacket = None
        self._output_queue: Queue[AudioPacket] = Queue()

    @property
    def frame_size(self):
        return self._frame_size

    def reset(self) -> None:
        self._command_audio_packet: AudioPacket = None
        self._tail_silence_start_timestamp: int = None
        self._reset_head_silences_buffer()

    def _reset_head_silences_buffer(self) -> None:
        """Reset silence buffer which is concatenated to the head of the utterance"""
        amount_to_keep_packets = (self._frame_size // 320) * (self._head_silence_buffer_size // 20)
        self._head_silences_buffer = collections.deque(maxlen=amount_to_keep_packets)
        self._num_recorded_chunks = 0

    def _concat_head_buffered_silences(self, audio_packet: AudioPacket) -> AudioPacket:
        """Concatenate buffered silence at the head of the utterance audio packet
        Args:
            audio_packet (AudioPacket): The audio packet to which the buffered silence will be concatenated.
        Returns:
            AudioPacket: The audio packet with the buffered silence concatenated at the head.
        """
        assert isinstance(audio_packet, AudioPacket), f"audio_packet must be AudioPacket, found {type(audio_packet)}"
        if not self._head_silences_buffer:
            # if there are no buffered silences, just return the audio packet
            logger.debug(f"No buffered silences, returning audio packet of duration {audio_packet.duration}")
            return audio_packet
        
        # if there are buffered silences, concatenate them to the head of the audio packet
        logger.debug(f"Concatenating {len(self._head_silences_buffer)} buffered silences to audio packet of duration {audio_packet.duration}")
        silences_audio_packet: AudioPacket = reduce(lambda x, y: x + y, self._head_silences_buffer)
        complete_frame = silences_audio_packet + audio_packet
        self._reset_head_silences_buffer()
        return complete_frame


    def feed(self, audio_packet: AudioPacket) -> None:
        """Feed audio packet to the VAD and process it.
        Args:
            audio_packet (AudioPacket): The audio packet to be processed.
        """
        assert isinstance(audio_packet, AudioPacket), f"audio_packet must be AudioPacket, found {type(audio_packet)}"
        if self.is_speech(audio_packet):
            if self._command_audio_packet is None:
                # start a new command audio packet if not already started
                self._command_audio_packet = self._concat_head_buffered_silences(audio_packet) # conatenate a bit of the buffered audio right before it.
                logger.success(f"Starting an utterance AudioPacket at {self._command_audio_packet.timestamp}")
            else:
                DEBUG__difference_between_start_to_end = audio_packet.timestamp - self._command_audio_packet.timestamp
                # TODO should I add silence/padding according to the difference between the start and end of the audio packet?
                # append to the existing on-going command audio packet
                self._command_audio_packet += audio_packet
            
        else:
            # silence detected    
            if self._command_audio_packet is not None:
                # if detected silence after voice, append silence to voice
                DEBUG__difference_between_start_to_end = audio_packet.timestamp - self._command_audio_packet.ending_timestamp
                # TODO should I add silence/padding according to the difference between the start and end of the audio packet?
                self._command_audio_packet += audio_packet

                # Check if silence threshold is reached ?? TODO
                if self._tail_silence_start_timestamp is None:
                    # if this is the first silence after voice, set the tail silence timestamp
                    self._tail_silence_start_timestamp: int = audio_packet.timestamp

                else:
                    # if this is not the first silence after voice, check if the silence duration is greater than the threshold so that we can send off the utterance                    
                    assert (audio_packet.ending_timestamp - self._command_audio_packet.ending_timestamp) == DEBUG__difference_between_start_to_end, \
                        f"Ending timestamp of new packet {audio_packet.ending_timestamp} - starting timestamp of command audio packet {self._command_audio_packet.ending_timestamp} should be equal to the difference between the start and end of the audio packet {DEBUG__difference_between_start_to_end} != {audio_packet.ending_timestamp - self._command_audio_packet.ending_timestamp}"
                    
                    now_timestamp: int = self._command_audio_packet.ending_timestamp  # TODO should now timestamp correspond to real time or to the end of the audio packet?

                    # TODO check latency of the audio packet receival
                    # the silence duration is the difference between the current timestamp and the tail silence starting timestamp
                    silence_duration: int = now_timestamp - self._tail_silence_start_timestamp

                    # logger.debug(f'Got Silence after voice duration: {silence_duration}')
                    if silence_duration >= self._tail_silence_threshold:
                        # if the silence duration is greater than the tail silence threshold, we can send off the utterance
                        self._output_queue.put(self._command_audio_packet)
                        logger.success(f"Utterance completed at {now_timestamp}, duration: {self._command_audio_packet.duration} ms")
                        self.log("\n[end]", force=True)
                        self.reset()

            else:
                # if no command audio packet is started, we can just buffer the silence
                self._head_silences_buffer.append(audio_packet)
    

    def get_utterance_if_any(self) -> Union[AudioPacket, None]:
        """Get the utterance if any is available in the output queue

        Returns:
            AudioPacket: The utterance audio packet if available, otherwise None
        """

        if self._output_queue.qsize() == 0:
            return None
        audio_packets = []
        while self._output_queue.qsize() > 0:
            audio_packet = self._output_queue.get_nowait()
            audio_packets.append(audio_packet)
        audio_packet: AudioPacket = reduce(lambda x, y: x + y, audio_packets)
        return audio_packet
    
    def is_speaking(self) -> bool:
        return self._command_audio_packet is not None and self._command_audio_packet.duration >= self._threshold_to_determine_speaking

    def log(self, msg, end="", force=False) -> None: # TODO: refactor out into progress logger
        """Log message to console if verbose is True or force is True with flush

        Args:
            msg (str): Message to log
            end (str, optional): End character. Defaults to "".
            force (bool, optional): Force logging. Defaults to False.

        """
        if self._verbose or force:
            write_output(msg, end=end)