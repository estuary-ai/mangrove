import webrtcvad
import torch
import collections
from abc import ABC, abstractmethod
from functools import reduce
from typing import Union, List
from .data_buffer import DataBuffer
from .audio_packet import AudioPacket


class VoiceActivityDetector(ABC):

    def __init__(
        self, silence_threshold: int = 200, frame_size: int = 320 * 3, verbose=False
    ):
        self.silence_threshold = silence_threshold
        self.frame_size = frame_size
        self.buffer = DataBuffer(self.frame_size)

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
            self._log("\n[start]", force=True)  # recording started
        else:
            self._log("=")  # still recording
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
                self._log("\n[end]", force=True)
                return True

        return False

    def _log(self, msg, end="", force=False):
        """Log message to console if verbose is True or force is True with flush

        Args:
            msg (str): Message to log
            end (str, optional): End character. Defaults to "".
            force (bool, optional): Force logging. Defaults to False.

        """
        if self.verbose or force:
            print(msg, end=end, flush=True)


class WebRTCVoiceActivityDetector(VoiceActivityDetector):

    def __init__(
        self,
        aggressiveness: int = 3,
        silence_threshold: int = 200,
        frame_size: int = 320 * 3,
        verbose=False,
    ):
        if frame_size not in [320, 640, 960]:
            raise ValueError("Frame size must be 320, 640 or 960 with WebRTC VAD")
        self.aggressiveness = aggressiveness
        self.model = webrtcvad.Vad(aggressiveness)
        super().__init__(silence_threshold, frame_size, verbose)

    def is_speech(self, audio_packets: Union[List[AudioPacket], AudioPacket]):
        """Check if audio is speech

        Args:
            audio_packet (AudioPacket): Audio packet to check

        Returns:
            bool: True if speech, False otherwise
        """
        one_item = False
        if not isinstance(audio_packets, list):
            audio_packets = [audio_packets]
            one_item = True

        is_speeches = []
        for packet in audio_packets:
            if len(packet) < self.frame_size:
                # partial TODO maybe add to buffer
                break
            audio_bytes, sample_rate = packet.bytes, packet.sample_rate
            is_speeches.append(self.model.is_speech(audio_bytes, sample_rate))

        # if any([not is_speech for is_speech in is_speeches]):
        #     self.model = webrtcvad.Vad(self.aggressiveness)

        if one_item:
            return is_speeches[0]
        return is_speeches

    def reset(self):
        super().reset()
        self.model = webrtcvad.Vad(self.aggressiveness)


class SileroVAD(VoiceActivityDetector):
    def __init__(
        self,
        device=None,
        threshold=0.5,
        silence_threshold: int = 200,
        frame_size: int = 512 * 4,
        verbose=False,
    ):
        if frame_size < 512 * 4:
            raise ValueError("Frame size must be at least 512*4 with Silero VAD")
        if device is None:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        elif device.startswith('cuda'):
            self.device = "cuda:0"
        else:
            self.device = "cpu"

        self.threshold = threshold
        self.model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
        self.model.to(device)

        # (get_speech_timestamps,
        # save_audio,
        # read_audio,
        # VADIterator,
        # collect_chunks) = utils
        # vad_iterator = VADIterator(model)
        super().__init__(silence_threshold, frame_size, verbose)

    def is_speech(self, audio_packets: Union[List[AudioPacket], AudioPacket]):
        """Check if audio is speech

        Args:
            audio_packet (AudioPacket): Audio packet to check

        Returns:
            bool: True if speech, False otherwise
        """
        one_item = False
        if not isinstance(audio_packets, list):
            audio_packets = [audio_packets]
            one_item = True

        is_speeches = []
        for packet in audio_packets:
            if len(packet) < self.frame_size:
                # partial TODO maybe add to buffer
                break
            _audio_tensor = torch.from_numpy(packet.float).to(self.device)
            is_speeches.append(
                self.model(_audio_tensor, packet.sample_rate) > self.threshold
            )

        # if any([not is_speech for is_speech in is_speeches]):
        #     self.model.reset_states()

        if one_item:
            return is_speeches[0]
        return is_speeches

    def reset(self):
        super().reset()
        self.model.reset_states()
