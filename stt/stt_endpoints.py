import time
import torch
from loguru import logger
from faster_whisper import WhisperModel
from queue import Queue, Empty
from .audio_packet import AudioPacket


class WhisperEndpoint:
    def __init__(self, model_name="guillaumekln/faster-whisper-tiny", device=None):
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        self.model = WhisperModel(model_name, device=self.device)
        self.input_queue = Queue()

    def buffer_audio_packet(self, audio_packet: AudioPacket):
        self.input_queue.put(audio_packet)

    def create_stream(self):
        self.reset()

    def get_transcription(self):
        print("Waiting for transcription ... ")
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

        # print('Transcribing ... ', f'{len(audio_packets)} packets')
        audio_packet = sum(audio_packets, AudioPacket.get_null_packet())
        print(
            "Transcribing ... ",
            f"{len(audio_packet)} bytes at {audio_packet.sample_rate} Hz",
        )

        # save this data as audio file
        # import scipy.io.wavfile as wav
        # wav.write('debug_audio.wav', audio_packet.sample_rate, audio_packet.float)

        # data = {
        #     'raw': audio_packet.float,
        #     'sampling_rate': audio_packet.sample_rate,
        # }
        # print('Transcribing ... ', f' at {data["sampling_rate"]} Hz')
        data = audio_packet.float

        start = time.time()
        # _out = self.model(data, generate_kwargs={"max_new_tokens": 128})
        segments, _ = self.model.transcribe(
            data,
            vad_filter=True,
        )
        _out = list(segments)
        if len(_out) > 1:
            logger.debug("detected {} segments".format(len(_out)))
        # print(_out)

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
