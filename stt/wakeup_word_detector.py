import numpy as np

from typing import Tuple, Generator
from datetime import datetime, timedelta
from .data_buffer import DataBuffer
from .audio_packet import AudioPacket
from .audio_classification_endpoint import HFAudioClassificationEndpoint


class WakeUpVoiceDetector:
    def __init__(
        self,
        audio_classification_endpoint_kwargs: dict = {
            "model_name": "MIT/ast-finetuned-speech-commands-v2",
            "prediction_prob_threshold": 0.85,
        },
        device="cuda",
        verbose=False,
    ):
        self.verbose = verbose
        self._audio_classifier = HFAudioClassificationEndpoint(
            **audio_classification_endpoint_kwargs, device=device
        )
        self.frame_size = self._audio_classifier.frame_size
        if self.frame_size is None:
            raise ValueError(f'Check implementation of {self._audio_classifier} for frame_size')
        self._input_buffer = DataBuffer(frame_size=self._audio_classifier.frame_size)

        stream_chunk_s = self._audio_classifier.frame_size / self._audio_classifier.sample_rate
        self._setup_params(stream_chunk_s=stream_chunk_s, chunk_length_s=2.0)

    def reset_data_buffer(self):
        """Reset data buffer"""
        self._input_buffer.reset()

    def feed_audio(self, audio_packet: AudioPacket):
        """Feed audio packet to buffer

        Args:
            audio_packet (AudioPacket): Audio packet to feed procupine hot-word detector
        """
        self._input_buffer.put(audio_packet)

    @staticmethod
    def chunk_bytes_iter(
        iterator: DataBuffer,
        chunk_len: int,
        stride: Tuple[int, int],
        stream: bool = False,
    ):
        """
        Reads raw bytes from an iterator and does chunks of length `chunk_len`. Optionally adds `stride` to each chunks to
        get overlaps. `stream` is used to return partial results even if a full `chunk_len` is not yet available.
        """
        acc = b""
        stride_left, stride_right = stride
        if stride_left + stride_right >= chunk_len:
            raise ValueError(
                f"Stride needs to be strictly smaller than chunk_len: ({stride_left}, {stride_right}) vs {chunk_len}"
            )

        _stride_left = 0
        while True:
            try:
                audio_packet = iterator.get(
                    frame_size=chunk_len + stride_left + stride_right, timeout=-1
                )
                # print(f"audio_packet {len(audio_packet)}: {audio_packet}")
            except DataBuffer.Empty:
                # logger.warning('no packets in buffer')
                break

            raw = audio_packet.bytes
            acc += raw
            if stream and len(acc) < chunk_len:
                stride = (_stride_left, 0)
                yield {"raw": acc[:chunk_len], "stride": stride, "partial": True}

            else:
                while len(acc) >= chunk_len:
                    # We are flushing the accumulator
                    stride = (_stride_left, stride_right)
                    item = {"raw": acc[:chunk_len], "stride": stride}
                    if stream:
                        item["partial"] = False
                    yield item
                    _stride_left = stride_left
                    acc = acc[chunk_len - stride_left - stride_right :]

        # Last chunk
        # if len(acc) > stride_left:
        #     item = {"raw": acc, "stride": (_stride_left, 0)}
        #     if stream:
        #         item["partial"] = False
        #     yield item

    def _setup_params(self, stream_chunk_s, chunk_length_s=0.5):
        # TODO add option to change format_for_conversion dynamically by audio_packet given format
        self.chunk_s = stream_chunk_s
        self.sampling_rate = self._audio_classifier.sample_rate
        self.dtype = np.float32
        self.size_of_sample = 4 # 32 bits because of float32

        stride_length_s = chunk_length_s/ 6

        self.chunk_len = int(round(self.sampling_rate * chunk_length_s)) * self.size_of_sample

        if isinstance(stride_length_s, (int, float)):
            stride_length_s = [stride_length_s, stride_length_s]

        self.stride_left = (
            int(round(self.sampling_rate * stride_length_s[0])) * self.size_of_sample
        )
        self.stride_right = (
            int(round(self.sampling_rate * stride_length_s[1])) * self.size_of_sample
        )

    def _preprocessed_mic(self) -> Generator:
        audio_time = datetime.now()
        delta = timedelta(
            seconds=self.chunk_s
        )  # TODO calculate based on timestamp of AudioPacket
        # logger.debug('starting processing...', end='', flush=True)
        for item in self.chunk_bytes_iter(
            self._input_buffer,
            self.chunk_len,
            stride=(self.stride_left, self.stride_right),
            stream=True,
        ):
            # print(">", end="", flush=True)
            # Put everything back in numpy scale
            item["raw"] = np.frombuffer(item["raw"], dtype=self.dtype).copy()
            item["stride"] = (
                item["stride"][0] // self.size_of_sample,
                item["stride"][1] // self.size_of_sample,
            )
            item["sampling_rate"] = self.sampling_rate

            audio_time += delta  # TODO fix audio time to match the transmitted time from AudioPacket
            if datetime.now() > audio_time + 10 * delta:  # TODO put back
                print(
                    f"time: {audio_time + 10 * delta};;; while now is {datetime.now()}; skipping ...",
                    end="",
                    flush=True,
                )
                # We're late !! SKIP
                continue
            yield item
        # logger.debug('quitting processing', flush=True)

    def is_wake_word_detected(self) -> bool:
        """Check if wake word is detected in the audio stream

        Returns:
            bool: True if wake word is detected
        """
        return self._audio_classifier.detect(self._preprocessed_mic())
