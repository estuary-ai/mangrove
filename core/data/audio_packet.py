import json
import numpy as np
from decimal import *
from typing import Type
from loguru import logger

from .data_packet import DataPacket


TARGET_SAMPLERATE = 16000


class AudioPacket(DataPacket):
    """Represents a "Packet" of audio data."""
    resampling = 0
    resampler = None

    def __init__(self, data_json, resample=True, is_processed=False):
        """Initialize AudioPacket from json data or bytes

        Args:
            data_json (dict or bytes): json data or bytes
        """
        if not isinstance(data_json, dict):
            data_json = json.loads(str(data_json))

        super().__init__(timestamp=data_json.get("timestamp"))

        self._src_sample_rate = int(data_json["sampleRate"])
        self._src_num_channels = int(data_json["numChannels"])
        self._src_sample_width = int(data_json["sampleWidth"])
        assert self._src_sample_width in [2, 4], f"Unhandled sample width `{self._src_sample_width}`. Please use `2` or `4`"

        if not is_processed:
            self._bytes = self._preprocess_audio_buffer(
                data_json.get("bytes", data_json.get("audio")),
                resample=resample
            )
        else:
            self._bytes = data_json["bytes"]

        self._src_frame_size = len(self._bytes)
        self._duration = data_json.get("duration")  # ms
        if self._duration is None:
            self._duration = (self._src_frame_size/ self._src_sample_rate) / (
                self._src_num_channels * 4
            )
            self._duration *= 1000  # ms

        # self._start = data_json.get("start", False)
        self._id = data_json.get("packetID")
        self._source = data_json.get("source", None)

        self._dst_sample_rate = self._src_sample_rate
        self._dst_num_channels = self._src_num_channels
        self._dst_sample_width = self._src_sample_width

    # @property
    # def start(self):
    #     return self._start

    @property
    def bytes(self):
        return self._bytes

    @property
    def float(self):
        """Get audio buffer as float

        Returns:
            np.array(float): audio buffer as float
        """
        # NOTE: adding silence to make sure the length is a multiple of 32
        # approximation to convert int16 to float32
        _bytes = self._bytes + b'0'*(len(self._bytes)%32)
        return np.frombuffer(_bytes, dtype=np.float32).copy()

    @property
    def sample_rate(self):
        return self._dst_sample_rate

    @property
    def sample_width(self):
        return self._dst_sample_width

    @property
    def num_channels(self):
        return self._dst_num_channels

    @property
    def frame_size(self):
        return len(self.bytes)

    @property
    def duration(self):
        return self._duration

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if self._id is not None:
            raise ValueError("Cannot change id once set")
        self._id = value

    def to_dict(self) -> dict:
        """Convert AudioPacket to dict

        Returns:
            dict: AudioPacket as dict
        """
        _dict = super().to_dict()
        _dict.update(
            {
                "bytes": self._bytes,
                "sampleRate": self.sample_rate,
                "sampleWidth": self.sample_width,
                "numChannels": self.num_channels,
                "duration": self.duration,
                # "start": self._start,
                "packetID": self.id,
            }
        )
        return _dict

    @staticmethod
    def verify_format(data_json):
        """Verify that data_json is in the correct format

        Args:
            data_json (dict): json data
        """
        for key in ["sampleRate", "bytes", "numChannels"]:
            if key not in data_json.keys():
                raise Exception(
                    f"Invalid AudioPacket format: {key} not in {data_json.keys()}"
                )

    def _preprocess_audio_buffer(self, buffer, resample=True):
        """Preprocess audio buffer to 16k 1ch int16 bytes format

        Args:
            buffer Union(np.array(float)): audio buffer
            sample_rate (int): sample rate of buffer
            num_channels (int): number of channels of buffer

        Returns:
            bytes: preprocessed audio buffer
        """

        # Convert to a NumPy array of float32
        self._dst_sample_width = 4
        if isinstance(buffer, bytes):
            if buffer == b"":
                # DUMMY AUX PACKET
                return buffer
            if self._src_sample_width == 2:
                buffer_float = np.frombuffer(buffer, dtype=np.int16).astype(np.float32)
            elif self._src_sample_width == 4:
                buffer_float = np.frombuffer(buffer, dtype=np.float32)
            else:
                raise ValueError(f"Unhandled sample width `{self._src_sample_width}`. Please use `2` or `4`")
        else:
            if self._src_sample_width == 2:
                buffer_float = np.fromstring(np.array(buffer, dtype=np.int16).tobytes(), dtype=np.float32)
            elif self._src_sample_width == 4:
                buffer_float = np.array(buffer).astype(np.float32)
            else:
                raise ValueError(f"Unhandled sample width `{self._src_sample_width}`. Please use `2` or `4`")


        # Merge Channels if > 1
        if self._src_num_channels > 1:
            # TODO revise
            # logger.warning(f"AudioPacket has {self._src_num_channels} channels, merging to 1 channel")
            one_channel_buffer = np.zeros(
                len(buffer_float) // self._src_num_channels, dtype=np.float32
            )
            channel_contribution = 1 / self._src_num_channels
            for i in range(len(one_channel_buffer)):
                for channel_i in range(self._src_num_channels):
                    one_channel_buffer[i] += (
                        buffer_float[i * self._src_num_channels + channel_i]
                        * channel_contribution
                    )
            self._dst_num_channels = 1
        else:
            one_channel_buffer = buffer_float

        if TARGET_SAMPLERATE != self._src_sample_rate and resample:
            self._bytes = one_channel_buffer.tobytes()
            self.resample(TARGET_SAMPLERATE, copy=False)
            self._dst_sample_rate = TARGET_SAMPLERATE
            return self._bytes
        else:
            return one_channel_buffer.tobytes()

    def resample(self, target_sample_rate, copy=True):
        # try:
        if target_sample_rate == self._src_sample_rate:
            return self

        # increment resampling counter
        AudioPacket.resampling += 1

        import torch
        from torchaudio import functional as F
        from torchaudio.transforms import Resample

        one_channel_buffer = np.frombuffer(self._bytes, dtype=np.float32)
        waveform = torch.from_numpy(one_channel_buffer.copy())

        # check if resampler is defined and matching the same sample rates
        if (
            AudioPacket.resampler is None
            or AudioPacket.resampler.orig_freq != self._src_sample_rate
            or AudioPacket.resampler.new_freq != target_sample_rate
        ):
            AudioPacket.resampler = Resample(self._src_sample_rate, target_sample_rate)
            logger.trace(f"Resampling {self._src_sample_rate} -> {target_sample_rate}")

        audio_resampled = AudioPacket.resampler(waveform)
        audio_resampled = audio_resampled.numpy().tobytes()

        if copy:
            from copy import deepcopy
            audio_packet = deepcopy(self)
            audio_packet._bytes = audio_resampled
            audio_packet._dst_sample_rate = target_sample_rate
            return audio_packet
        else:
            self._bytes = audio_resampled
            self._dst_sample_rate = target_sample_rate
            return self

    def __add__(self, _other: Type["AudioPacket"]):
        """Add two audio packets together and return new packet with combined bytes

        Args:
            _other (AudioPacket): AudioPacket to add

        Returns:
            AudioPacket: New AudioPacket with combined bytes
        """
        # ensure no errs, and snippets are consecutive
        # TODO verify + duration work
        if self > _other:
            raise Exception(
                f"Audio Packets are not in order: {self.timestamp} > {_other.timestamp}"
            )

        # assert not (not self._start and _other._start)
        assert self.sample_rate == _other.sample_rate, f"Sample rates do not match: {self.sample_rate} != {_other.sample_rate}"
        assert self.num_channels == _other.num_channels, f"Num channels do not match: {self.num_channels} != {_other.num_channels}"
        assert self.sample_width == _other.sample_width, f"Sample width do not match: {self.sample_width} != {_other.sample_width}"
        # assert self.timestamp + self.duration <= _other.timestamp, f"Audio Packets are not consecutive: {self.timestamp} + {self.duration} = {self.timestamp + self.duration} > {_other.timestamp}"
        # if self.timestamp + self.duration > _other.timestamp:
        #     import math
        #     if math.isclose(self.timestamp + self.duration, _other.timestamp, abs_tol=500): # 500 ms tolerance
        #         _other.timestamp = self.timestamp + self.duration
        #     else:
        #         raise Exception(
        #             f"Audio Packets are not consecutive: {self.timestamp} + {self.duration} > {_other.timestamp}, {self.timestamp + self.duration - _other.timestamp}"
        #         )

        timestamp = self.timestamp
        if self._bytes == b"":  # DUMMY AUX PACKET
            timestamp = _other.timestamp

        return AudioPacket(
            {
                "bytes": self.bytes + _other.bytes,
                "timestamp": timestamp,
                "sampleRate": self.sample_rate,
                "numChannels": self.num_channels,
                "sampleWidth": self.sample_width,
                # "start": self._start,
                "packetID": self.id
            },
            resample=False,
            is_processed=True,
        )

    def __getitem__(self, key):
        """Get item from AudioPacket

        Args:
            key (int or slice): index or slice

        Returns:
            AudioPacket: new AudioPacket with sliced bytes
        """
        if isinstance(key, slice):
            # Note that step != 1 is not supported
            start, stop, step = key.indices(len(self))
            if step != 1:
                raise (NotImplementedError, "step != 1 not supported")

            if start < 0:
                raise (NotImplementedError, "start < 0 not supported")

            if stop > len(self):
                raise (NotImplementedError, "stop > len(self) not supported")

            # calculate new timestamp
            calculated_timestamp = (
                self.timestamp + float((start / self.frame_size)) * self.duration
            )

            return AudioPacket(
                {
                    "bytes": self._bytes[start:stop],
                    "timestamp": calculated_timestamp,
                    "sampleRate": self.sample_rate,
                    "numChannels": self.num_channels,
                    "sampleWidth": self.sample_width,
                    # "start": self._start,
                    "packetID": self._id
                },
                resample=False,
                is_processed=True,
            )

        elif isinstance(key, int):
            raise NotImplementedError("value as index; only slices")
        elif isinstance(key, tuple):
            raise NotImplementedError("Tuple as index; only slices")
        else:
            raise TypeError("Invalid argument type: {}".format(type(key)))

    def __eq__(self, __o: object) -> bool:
        return self.timestamp == __o.timestamp

    def __lt__(self, __o: object) -> bool:
        # TODO verify + duration work
        # return self.timestamp + self._duration <= __o.timestamp
        return self.timestamp < __o.timestamp

    def __len__(self) -> int:
        return self.frame_size

    def play(self):
        import sounddevice as sd
        sd.play(self.float, self.sample_rate)