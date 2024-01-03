import time
import threading
import numpy as np
from typing import Tuple
from datetime import datetime, timedelta
from loguru import logger
# from transformers.pipelines.audio_utils import chunk_bytes_iter
from .data_buffer import DataBuffer
from .audio_packet import AudioPacket


class WakeUpVoiceDetector:
    def __init__(
        self,
        model_name="MIT/ast-finetuned-speech-commands-v2",
        wake_word="marvin",
        device="cuda",
        verbose=False,
    ):
        self.verbose = verbose
        self.frame_size = 1024
        self._input_buffer = DataBuffer(self.frame_size)

        self._lock = threading.Lock()
        self._output = [False]

        from transformers import pipeline

        self._classifier = pipeline(
            "audio-classification", model=model_name, device=device
        )

        if wake_word not in self._classifier.model.config.label2id.keys():
            raise ValueError(
                f"Wake word {wake_word} not in set of valid class labels,"
                f"pick a wake word in the set {self._classifier.model.config.label2id.keys()}."
            )

        self.wake_word = wake_word

        logger.info(
            f"Wakeword set is {self.wake_word} out of {self._classifier.model.config.label2id.keys()}"
        )

    def reset_data_buffer(self):
        """Reset data buffer"""
        self._input_buffer.reset()

    def feed_audio(self, audio_packet: AudioPacket):
        """Feed audio packet to buffer

        Args:
            audio_packet (AudioPacket): Audio packet to feed procupine hot-word detector
        """
        try:
            self._input_buffer.put(audio_packet)
        except:
            # TODO remove this .. just for debugging purposes now as the wake up word detector classifier not working yet
            pass
            # self.reset_data_buffer()


    @staticmethod
    def chunk_bytes_iter(iterator: DataBuffer, chunk_len: int, stride: Tuple[int, int], stream: bool = False):
        """
        Reads raw bytes from an iterator and does chunks of length `chunk_len`. Optionally adds `stride` to each chunks to
        get overlaps. `stream` is used to return partial results even if a full `chunk_len` is not yet available.
        """
        acc = b""
        stride_left, stride_right = stride
        if stride_left + stride_right >= chunk_len:
            raise ValueError(f"Stride needs to be strictly smaller than chunk_len: ({stride_left}, {stride_right}) vs {chunk_len}")

        _stride_left = 0
        while True:
            try:
                audio_packet = iterator.get(frame_size=chunk_len + stride_left + stride_right, timeout=-1)
            except:
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

    def _preprocessed_mic(self, format_for_conversion='f32le'):
        # arbitrary values
        chunk_length_s = 2.0
        stream_chunk_s = 0.25

        if stream_chunk_s is not None:
            chunk_s = stream_chunk_s
        else:
            chunk_s = chunk_length_s


        sampling_rate = self._classifier.feature_extractor.sampling_rate

        if format_for_conversion == "s16le":
            dtype = np.int16
            size_of_sample = 2
        elif format_for_conversion == "f32le":
            dtype = np.float32
            size_of_sample = 4
        else:
            raise ValueError(f"Unhandled format `{format_for_conversion}`. Please use `s16le` or `f32le`")

        stride_length_s = chunk_length_s / 6

        chunk_len = int(round(sampling_rate * chunk_length_s)) * size_of_sample
        if isinstance(stride_length_s, (int, float)):
            stride_length_s = [stride_length_s, stride_length_s]

        stride_left = int(round(sampling_rate * stride_length_s[0])) * size_of_sample
        stride_right = int(round(sampling_rate * stride_length_s[1])) * size_of_sample

        audio_time = datetime.now()
        delta = timedelta(seconds=chunk_s) # TODO calculate based on timestamp of AudioPacket
        # logger.debug('starting processing...', end='', flush=True)
        for item in self.chunk_bytes_iter(
            self._input_buffer, chunk_len, stride=(stride_left, stride_right), stream=True
        ):
            # print(">", end="", flush=True)
            # Put everything back in numpy scale
            item["raw"] = np.frombuffer(item["raw"], dtype=dtype).copy()
            item["stride"] = (
                item["stride"][0] // size_of_sample,
                item["stride"][1] // size_of_sample,
            )
            item["sampling_rate"] = sampling_rate

            audio_time += delta # TODO fix audio time to match the transmitted time from AudioPacket
            if datetime.now() > audio_time + 10 * delta: # TODO put back
                print(f'time: {audio_time + 10 * delta};;; while now is {datetime.now()}; skipping ...', end='', flush=True)
                # We're late !! SKIP
                continue
            yield item
        # logger.debug('quitting processing', flush=True)


    def run(self):
        pass
        # def _classify(prob_threshold=0.5):
        #     time.sleep(5)
        #     for prediction in self._classifier(self._preprocessed_mic()):
        #         print('<<<', end="", flush=True)
        #         prediction = prediction[0]
        #         if prediction["label"] == self.wake_word:
        #             if prediction["score"] > prob_threshold:
        #                 print("Wake word detected!")
        #                 with self._lock:
        #                     self._output[0] += True

        # self._thread = threading.Thread(target=_classify, args=(0.5,), daemon=True)
        # self._thread.start()
        # logger.success('running wake up word detector')

    # def is_wake_word_detected(self) -> bool:
    #     """Return True if wake word is detected

    #     Returns:
    #         bool: True if wake word is detected
    #     """
    #     with self._lock:
    #         _out = self._output[0]
    #         self._output[0] = False
    #         return _out

    def is_wake_word_detected(self) -> bool:
        prob_threshold = 0.7
        is_detected = False
        for prediction in self._classifier(self._preprocessed_mic()):
            print('<', end="", flush=True)
            prediction = prediction[0]
            if prediction["label"] == self.wake_word:
                if prediction["score"] > prob_threshold:
                    is_detected = True
                    break
        if is_detected:
            return True
        return False