import torch
from typing import Optional, List

from core.utils import logger
from core.stage import AudioToAudioStage
from core.stage.base import QueueEmpty, SequenceMismatchException
from core import AudioPacket
from .endpoints.silero import SileroVAD



class VADStage(AudioToAudioStage):
    def __init__(
        self,
        device: str = None,
        verbose: bool = False,
        **endpoint_kwargs
    ):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._endpoint = SileroVAD(
            **endpoint_kwargs,
            device=device,
            verbose=verbose
        )

        super().__init__(frame_size=self._endpoint.frame_size, verbose=verbose)

    def _unpack(self) -> AudioPacket:
        """Unpack audio packets from input buffer"""
        data_packets: List[AudioPacket] = self._intermediate_input_buffer
        self._intermediate_input_buffer = []

        if not self._intermediate_input_buffer: # if intermediate buffer is empty, we need to get at least one packet from input buffer
            data_packet = self._input_buffer.get(timeout=None) # blocking call at least for the first time
            data_packets.append(data_packet)
        else:
            logger.debug("Intermediate buffer is not empty, skipping first get from input buffer")

        # Now we have at least one packet in data_packets, we can try to get more packets
        while True:
            try:
                data_packet = self._input_buffer.get_nowait()
                data_packets.append(data_packet)
            except QueueEmpty:
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

    def start(self, host):
        """Start processing thread"""
        logger.info(f'Starting {self}')

        self._host = host

        self.on_start()

        def _start_thread():
            while True:
                with self._lock:
                    data = self._unpack()
                    assert isinstance(data, AudioPacket), f"Expected AudioPacket, got {type(data)}"
                    data_packet = self._process(data)
                    
                    if self._is_interrupt_signal_pending:
                        logger.warning(f"Interrupt signal pending in {self.__class__.__name__}, calling on_interrupt")
                        self.on_interrupt()

                    if data_packet is not None and not isinstance(data_packet, bool):
                        # TODO this is just hacky way.. use proper standards
                        self.on_ready(data_packet)
                    

        self._processor = self._host.start_background_task(_start_thread)


    def _process(self, audio_packet: AudioPacket) -> Optional[AudioPacket]:
        assert isinstance(audio_packet, AudioPacket), f"Expected AudioPacket, got {type(audio_packet)}"

        if len(audio_packet) < self.frame_size:
            raise NotImplementedError("Partial audio packet found; this should not happen")
        
        self._endpoint.feed(audio_packet)

        if self._endpoint.is_speaking():
            self.schedule_forward_interrupt()

        audio_packet_utterance = self._endpoint.get_utterance_if_any() 
        if audio_packet_utterance:
            # self.refresh()
            return audio_packet_utterance

    def reset_audio_stream(self) -> None:
        """Reset audio stream context"""
        self._endpoint.reset()

    # TODO use after some detection
    def refresh(self) -> None:
        """Refresh audio stream"""
        self.reset_audio_stream()

    def on_disconnect(self) -> None:
        self.reset_audio_stream()
