import torch
from typing import Optional, List

from core.data import TextPacket, AudioPacket, AudioBuffer, DataBuffer, DataBufferEmpty
from core.stage import AudioToTextStage
from core.stage.base import SequenceMismatchException
from core.utils import Timer, logger
from .endpoints.faster_whisper import FasterWhisperEndpoint


class STTStage(AudioToTextStage):
    """Speech to Text Stage"""

    def __init__(
        self,
        frame_size=512 * 4,
        device=None,
        verbose=False,
    ):
        """Initialize STT Stage

        Args:
            frame_size (int, optional): audio frame size. Defaults to 320.
            device (str, optional): Device to use. Defaults to None.
            verbose (bool, optional): Whether to print debug messages. Defaults to False.

        Raises:
            ValueError: If custom scorer is defined but not found
        """
        super().__init__(frame_size=frame_size, verbose=verbose)

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._endpoint = FasterWhisperEndpoint(device=device)  # TODO make selection dynamic by name or type

        self._recorded_audio_length: int = 0  # FOR DEBUGGING
        self._interrupted_audio_packet: Optional[AudioPacket] = None
        
    def unpack(self) -> TextPacket:
        """Unpack data from input buffer and return a complete DataPacket
        This method collects data packets from the input buffer and combines them into a single DataPacket, that can be processed by the next stage in the pipeline.
        """
        if self.input_buffer is None:
            raise RuntimeError("Input buffer is not set. Please set the input buffer before unpacking data.")
        
        logger.warning("Unpacking data from input buffer")

        data_packets: List[TextPacket] = self._intermediate_input_buffer
        self._intermediate_input_buffer = []

        if not data_packets:  # if intermediate buffer is empty, we need to get at least one packet from input buffer
            logger.warning("Intermediate buffer is empty, getting first data packet from input buffer")
            data_packet = self.input_buffer.get()  # blocking call at least for the first time
            data_packets.append(data_packet)
            logger.warning(f"Got first data packet: {data_packet}")
        else:
            logger.debug("Intermediate buffer is not empty, skipping first get from input buffer")

        # Now we have at least one packet in data_packets, we can try to get more packets
        while True:
            try:
                data_packet = self.input_buffer.get_nowait()
                data_packets.append(data_packet)
            except DataBufferEmpty:
                # if len(data_packets) == 0:
                #     # logger.warning('No audio packets found in buffer', flush=True)
                #     return
                break

        complete_data_packet = data_packets[0]
        for i, data_packet in enumerate(data_packets[1:], start=1):
            try:
                complete_data_packet += data_packet
            except SequenceMismatchException as e:
                for j in range(i, len(data_packets)):
                    self._intermediate_input_buffer.append(data_packets[j])
                break
        
        return complete_data_packet

    def on_start(self):
        self._recorded_audio_length = 0  # FOR DEBUGGING
        self._interrupted_audio_packet = None

    def reset_audio_stream(self, reset_buffers=True) -> None:
        """Reset audio stream context"""
        if reset_buffers:
            self.log("[stt-hard-reset]", end="\n")
            self._endpoint.reset()
            self.input_buffer.reset()
            self._interrupted_audio_packet = None
        else:
            self.log("[stt-soft-reset]", end=" ")
        self._recorded_audio_length = 0

    def process(self, audio_packet) -> None:
        """Process audio buffer and return transcription if any found"""
        assert isinstance(audio_packet, AudioPacket), f"Expected AudioPacket, got {type(audio_packet)}"

        if len(audio_packet) < self.frame_size:
            raise Exception("Partial audio packet found; this should not happen")

        # Feed audio content to stream context
        logger.info(f"Processing {audio_packet}")
        if self._interrupted_audio_packet is not None:
            logger.debug("Interrupted audio packet found, appending at head")
            audio_packet = self._interrupted_audio_packet + audio_packet
            self._interrupted_audio_packet = None
        self._recorded_audio_length += audio_packet.duration # FOR DEBUGGING
        
        self._endpoint.feed(audio_packet) # TODO maybe merge with get_transcription_if_any()

        # Finish stream and return transcription if any found
        # logger.debug("Trying to finish stream..")
        with Timer() as timer:
            transcription: Optional[str] = self._endpoint.get_transcription_if_any()
            if transcription:
                self.reset_audio_stream(reset_buffers=False)
                self.pack(
                    TextPacket(
                        text=transcription,
                        partial=True,  # TODO is it?
                        start=False,
                        recog_time=timer.record(),
                        recorded_audio_length=self._recorded_audio_length,
                    )
                )  # put transcription to the output buffer


    def on_disconnect(self) -> None:
        self.reset_audio_stream()
        self.log("[disconnect]", end="\n")

    def on_interrupt(self):
        super().on_interrupt()
        # pack the data from endpoint to buffer
        self._interrupted_audio_packet = self._endpoint.get_buffered_audio_packet()
        while True:
            try:
                audio_packet = self.input_buffer.get_nowait()
                if self._interrupted_audio_packet is None:
                    self._interrupted_audio_packet = audio_packet
                else:
                    self._interrupted_audio_packet += audio_packet
            except DataBufferEmpty:
                break
        self.reset_audio_stream(reset_buffers=False)
        self.log("[interrupt]", end=" ")