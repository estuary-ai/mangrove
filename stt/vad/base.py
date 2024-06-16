import collections
from functools import reduce
from abc import ABCMeta, abstractmethod
from functools import reduce
from typing import Union, List
from storage_manager import write_output
from core import AudioBuffer, AudioPacket

class VoiceActivityDetector(metaclass=ABCMeta):

    def __init__(
        self, silence_threshold: int = 200, frame_size: int = 320 * 3, verbose=False
    ):
        self.silence_threshold = silence_threshold
        self.frame_size = frame_size
        self.buffer = AudioBuffer(self.frame_size)

        self.buffered_silences = collections.deque(maxlen=2)
        self.verbose = verbose
        self.reset()

    def reset(self):
        self.num_recorded_chunks = 0
        self.silence_frame_start_timestamp = None
        self._reset_silence_buffer()

    def _reset_silence_buffer(self):
        """Reset silence buffer"""
        # TODO try increasing size
        self.buffered_silences = collections.deque(maxlen=2)
        self.num_recorded_chunks = 0

    @abstractmethod
    def is_speech(self, audio_packets: Union[List[AudioPacket], AudioPacket]):
        raise NotImplementedError

    def detected_silence_after_voice(self, frame: AudioPacket):
        if self.num_recorded_chunks > 0:
            return True
        else:
            # print('Silence before any voice')
            # VAD has a tendency to cut the first bit of audio data
            # from the start of a recording
            # so keep a buffer of that first bit of audio and
            # in addBufferedSilence() reattach it to the beginning of the recording
            self.buffered_silences.append(frame)
            return False

    def process_voice(self, frame: AudioPacket):
        """Process voice frame

        Args:
            frame (AudioPacket): Audio packet of voice frame

        Returns:
            AudioPacket: Audio packet of voice frame with silence buffer appended
        """

        def _concat_buffered_silence(frame: AudioPacket):
            """Concatenate buffered silence to voice frame"""

            if len(self.buffered_silences) > 0:
                # if there were silence buffers append them
                # DEBUG START
                silence_len = reduce(
                    lambda x, y: len(x) + len(y), self.buffered_silences
                )
                if isinstance(silence_len, AudioPacket):
                    silence_len = len(silence_len)

                # DEBUG END
                self.buffered_silences.append(frame)
                complete_frame = reduce(lambda x, y: x + y, self.buffered_silences)
                self._reset_silence_buffer()
            else:
                complete_frame = frame
            return complete_frame

        self.silence_frame_start_timestamp = None
        if self.num_recorded_chunks == 0:
            self.log("\n[start]", force=True)  # recording started
        else:
            self.log("=")  # still recording
        self.num_recorded_chunks += 1
        frame_inc_silence = _concat_buffered_silence(frame)

        return frame_inc_silence

    def is_silence_cross_threshold(self, frame: AudioPacket):
        """Check if silence threshold is reached

        Args:
            frame (AudioPacket): Audio packet of silence frame

        Returns:
            bool: True if silence threshold is reached, False otherwise
        """
        if self.silence_frame_start_timestamp is None:
            self.silence_frame_start_timestamp = frame.timestamp
            # self.silence_frame_start_timestamp = frame.timestamp + frame.duration
        else:
            now_timestamp = frame.timestamp + frame.duration
            silence_duration = now_timestamp - self.silence_frame_start_timestamp
            # logger.debug(f'Got Silence after voice duration: {silence_duration}')
            if silence_duration >= self.silence_threshold:
                # logger.info(f'Got Silence duration: {silence_duration}, threshold: {self.silence_threshold}')
                self.silence_frame_start_timestamp = None
                self.log("\n[end]", force=True)
                return True

        return False

    def log(self, msg, end="", force=False):
        """Log message to console if verbose is True or force is True with flush

        Args:
            msg (str): Message to log
            end (str, optional): End character. Defaults to "".
            force (bool, optional): Force logging. Defaults to False.

        """
        if self.verbose or force:
            write_output(msg, end=end)