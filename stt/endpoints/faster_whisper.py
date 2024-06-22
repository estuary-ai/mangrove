import time
from loguru import logger
from queue import Empty
from functools import reduce
from faster_whisper import WhisperModel

from core import AudioPacket
from .base import STTEndpoint

class FasterWhisperEndpoint(STTEndpoint):
    def __init__(self, model_name="base.en", device=None):
        super().__init__()
        self.device = "auto" if device is None else device
        try:
            self.model = WhisperModel(model_name, device=self.device)
        except:
            logger.warning(f'Device {device} is not supported, defaulting to CPU!')
            self.model = WhisperModel(model_name, device='cpu')
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

        audio_packet: AudioPacket = reduce(lambda x, y: x + y, audio_packets)
        start = time.time()
        segments, _ = self.model.transcribe(
            audio_packet.float,
            language='en',
            vad_filter=True,
            without_timestamps=True
        )
        _out = list(segments)
        if len(_out) >= 1:
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
