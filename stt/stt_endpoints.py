import time
import torch
from loguru import logger
from faster_whisper import WhisperModel
from queue import Queue, Empty
from .audio_packet import AudioPacket


class WhisperEndpoint:
    def __init__(self, model_name="base.en", device=None):
        self.device = "auto" if device is None else device
        try:
            self.model = WhisperModel(model_name, device=self.device)
        except:
            logger.warning(f'Device {device} is not supported, defaulting to CPU!')
            self.model = WhisperModel(model_name, device='cpu')
        self.input_queue = Queue()

    def buffer_audio_packet(self, audio_packet: AudioPacket):
        self.input_queue.put(audio_packet)

    def create_stream(self):
        self.reset()

    def get_transcription(self):
        logger.trace("Waiting for transcription ... ")
        if self.input_queue.qsize() == 0:
            return None

        # unpack as many as possible from queue
        while self.input_queue.qsize() > 0:
            audio_packets = []
            while True:
                try:
                    audio_packet = self.input_queue.get_nowait()
                    audio_packets.append(audio_packet)
                except Empty:
                    break

        audio_packet = sum(audio_packets, AudioPacket.get_null_packet())
        logger.debug(
            f"Transcribing ... {len(audio_packet)} bytes at {audio_packet.sample_rate} Hz"
        )
        start = time.time()
        segments, _ = self.model.transcribe(audio_packet.float, vad_filter=True, without_timestamps=True)
        _out = list(segments)
        if len(_out) >= 1:
            logger.debug("detected {} segments".format(len(_out)))
            _out = " ".join([segment.text for segment in _out])
        logger.success(f"Took {time.time() - start: < .3f} seconds")
        return _out

    def reset(self):
        while True:
            try:
                self.input_queue.get_nowait()
            except Empty:
                break
        logger.debug("Resetting ...")
        # self.output_queue.queue.clear()
