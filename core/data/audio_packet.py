import json
import numpy as np
from decimal import *
from typing import Type
from loguru import logger

from .data_packet import DataPacket

class AudioPacket(DataPacket):
    """Represents a "Packet" of audio data."""
    resampling = 0

    def __init__(self, data_json, resample=True, is_processed=False, target_sample_rate=16000):
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
        
        self._dst_sample_rate = self._src_sample_rate
        self._dst_num_channels = self._src_num_channels
        self._dst_sample_width = self._src_sample_width


        # self._start = data_json.get("start", False)
        self._id = data_json.get("packetID")
        self._source = data_json.get("source", None)


        # NOTE: we do not keep the src_bytes as they might not be even there
        if not is_processed:
            self._dst_bytes = self._preprocess_audio_buffer(
                data_json.get("bytes", data_json.get("audio")),
                resample=resample,
                target_sample_rate=target_sample_rate
            )
        else:
            self._dst_bytes = data_json["bytes"]

        # NOTE: this is happening after the resampling and processing
        self._duration = data_json.get("duration")  # ms
        _calculated_duration = (self.frame_size/self.sample_rate) / (
            self.num_channels * self.sample_width # this was 4, i changed it to self.sample_width, TODO check
        )
        _calculated_duration *= 1000  # ms
        
        if self._duration is None:
            self._duration = _calculated_duration
        else:
            # Verify that the duration is correct for now
            if not Decimal(self._duration).compare(Decimal(_calculated_duration)) == 0:
                logger.warning(f"Duration mismatch: {self._duration} != {_calculated_duration}")    

        
            

    # @property
    # def start(self):
    #     return self._start

    @property
    def bytes(self):
        return self._dst_bytes

    @property
    def float(self):
        """Get audio buffer as float

        Returns:
            np.array(float): audio buffer as float
        """
        # NOTE: adding silence to make sure the length is a multiple of 32
        # approximation to convert int16 to float32
        _bytes = self.bytes + b'0'*(len(self.bytes)%32)
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
                "bytes": self.bytes,
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
            
        
    @staticmethod
    def from_bytes_to_float(buffer, sample_rate, num_channels, sample_width):
        """Convert audio buffer from bytes to float

        Args:
            buffer (bytes): audio buffer
            sample_rate (int): sample rate of buffer
            num_channels (int): number of channels of buffer
            sample_width (int): sample width of buffer

        Returns:
            np.array(float): audio buffer as float
        """
        if buffer == b"":
            logger.debug("0 Returning empty buffer")
            # DUMMY AUX PACKET
            return buffer
        
        if sample_width == 2: # int16
            logger.debug("1 Converting buffer to int16")
            buffer_float = np.frombuffer(buffer, dtype=np.int16).reshape((-1, num_channels)) / (1 << (8 * sample_width - 1))
            # import soundfile as sf
            # sf.write(f"__original_{AudioPacket.resampling}.wav", buffer_float, sample_rate)
        elif sample_width == 4: # float32
            logger.debug("1 Converting buffer to float32")
            buffer_float = np.frombuffer(buffer, dtype=np.float32).reshape((-1, num_channels)) / (1 << (8 * sample_width - 1))
        else:
            raise ValueError(f"Unhandled format `{format}`. Please use `int16` or `float32`")
        
        return buffer_float
    
    @staticmethod
    def from_float_to_bytes(buffer_float, sample_rate, num_channels, sample_width):
        """Convert audio buffer from float to bytes

        Args:
            buffer_float (np.array(float)): audio buffer
            sample_rate (int): sample rate of buffer
            num_channels (int): number of channels of buffer
            sample_width (int): sample width of buffer

        Returns:
            bytes: audio buffer as bytes
        """
        if buffer_float.size == 0:
            logger.debug("0 Returning empty buffer")
            # DUMMY AUX PACKET
            return buffer_float.tobytes()

        if sample_width == 2: # int16
            logger.debug("1 Converting buffer to int16")
            buffer = (buffer_float * (1 << (8 * sample_width - 1))).astype(np.int16).reshape(-1).tobytes()
        elif sample_width == 4: # float32
            logger.debug("1 Converting buffer to float32")
            buffer = (buffer_float * (1 << (8 * sample_width - 1))).astype(np.float32).reshape(-1).tobytes()
        else:
            raise ValueError(f"Unhandled sample width `{sample_width}`. Please use `2` or `4` ")

        return buffer
    
    def _preprocess_audio_buffer(self, buffer, resample=True, target_sample_rate=16000):
        """Preprocess audio buffer to 16k 1ch int16 bytes format

        Args:
            buffer Union(np.array(float), bytes): audio buffer
            sample_rate (int): sample rate of buffer
            num_channels (int): number of channels of buffer

        Returns:
            bytes: preprocessed audio buffer
        """

        # TODO remove format as it is the same as sample_width
        # 1: Convert to a NumPy array of float32
        self._dst_sample_width = 2 # TODO debug this
        if isinstance(buffer, bytes):
            # 1.1: converting/ensuring a bytes buffer to np.array float32 from either 2 or 4 sample width
            buffer_float = AudioPacket.from_bytes_to_float(
                buffer, self._src_sample_rate, 
                self._src_num_channels, self._src_sample_width
            )
        else:
            # 1.2: converting/ensuring a np.array buffer to np.array float32 from either 2 or 4 sample width
            if self._src_sample_width == 2:
                buffer_float = np.fromstring(np.array(buffer, dtype=np.int16).tobytes(), dtype=np.float32)
            elif self._src_sample_width == 4:
                buffer_float = np.array(buffer).astype(np.float32)
            else:
                raise ValueError(f"Unhandled sample width `{self._src_sample_width}`. Please use `2` or `4`")
            
        # 2: Merge Channels if > 1
        if self._src_num_channels > 1:
            # TODO revise
            logger.warning(f"AudioPacket has {self._src_num_channels} channels, merging to 1 channel")
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


        # 3: Resample if necessary
        final_buffer = one_channel_buffer
        if target_sample_rate != self._src_sample_rate and resample:
            # debug resampling TODO
            audio_resampled = AudioPacket.resample(one_channel_buffer, self._src_sample_rate, target_sample_rate)
            AudioPacket.resampling += 1
            self._dst_sample_rate = target_sample_rate
            final_buffer = audio_resampled
        
        if isinstance(buffer, bytes):
            self._dst_bytes = AudioPacket.from_float_to_bytes(
                final_buffer,
                self._dst_sample_rate,
                self._dst_num_channels,
                self._dst_sample_width,
            )
        else:
            self._dst_bytes = final_buffer.tobytes()

        return self._dst_bytes

    @staticmethod
    def resample(waveform, current_sample_rate, target_sample_rate):
        # try:
        if target_sample_rate == current_sample_rate:
            return waveform

        import torch
        from torchaudio.transforms import Resample

        if current_sample_rate > target_sample_rate:
            waveform = torch.from_numpy(waveform.copy())

            # check if resampler is defined and matching the same sample rates
            resampler = Resample(current_sample_rate, target_sample_rate, dtype=waveform.dtype)
            logger.debug(f"Resampling {current_sample_rate} -> {target_sample_rate}")

            audio_resampled = resampler(waveform).numpy()
        else:
            # TODO revise this
            # if  target_sample_rate % current_sample_rate == 0:
            #     rate = target_sample_rate // current_sample_rate
            #     audio_resampled = np.zeros(rate*len(waveform)-rate+1, dtype=waveform.dtype)
            #     audio_resampled[::rate] = waveform
            #     audio_resampled[1::rate] = (waveform[:-1] + waveform[1:]) / 2
            # else:
            audio_resampled = np.zeros(int(len(waveform) * target_sample_rate / current_sample_rate), dtype=waveform.dtype)
            for i in range(len(audio_resampled)):
                audio_resampled[i] = waveform[int(i * current_sample_rate / target_sample_rate)]

        # write the resampled audio to a wav file
        # import soundfile as sf
        # sf.write(f"resampled_{AudioPacket.resampling}.wav", audio_resampled, target_sample_rate)
        # sf.write(f"original_{AudioPacket.resampling}.wav", waveform, current_sample_rate)

        return audio_resampled

    def __add__(self, _audio_packet: Type["AudioPacket"]):
        """Add two audio packets together and return new packet with combined bytes

        Args:
            _audio_packet (AudioPacket): AudioPacket to add

        Returns:
            AudioPacket: New AudioPacket with combined bytes
        """
        # ensure no errs, and snippets are consecutive
        # TODO verify + duration work
        if self > _audio_packet:
            raise Exception(
                f"Audio Packets are not in order: {self.timestamp} > {_audio_packet.timestamp}"
            )

        # assert not (not self._start and _other._start)
        assert self.sample_rate == _audio_packet.sample_rate, f"Sample rates do not match: {self.sample_rate} != {_audio_packet.sample_rate}"
        assert self.num_channels == _audio_packet.num_channels, f"Num channels do not match: {self.num_channels} != {_audio_packet.num_channels}"
        assert self.sample_width == _audio_packet.sample_width, f"Sample width do not match: {self.sample_width} != {_audio_packet.sample_width}"
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
        if self.bytes == b"":  # DUMMY AUX PACKET
            timestamp = _audio_packet.timestamp

        return AudioPacket(
            {
                "bytes": self.bytes + _audio_packet.bytes,
                "timestamp": timestamp,
                "sampleRate": _audio_packet.sample_rate,
                "numChannels": _audio_packet.num_channels,
                "sampleWidth": _audio_packet.sample_width,
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
                    "bytes": self.bytes[start:stop],
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
        
    
    def __str__(self) -> str:
        return f"{self.timestamp}, {self._duration}, {len(self.bytes)}"

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