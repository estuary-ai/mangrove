import torch
from typing import Optional

from core.stage import AudioToAudioStage
from core import AudioBuffer, AudioPacket
from core.utils import logger
from .endpoints.silero import SileroVAD



class VADStage(AudioToAudioStage):
    def __init__(
        self,
        name: str,
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
        # self._endpoint._output_queue = self._output_buffer # TODO the output queue is set to the stage's output buffer
        super().__init__(name=name, frame_size=self._endpoint.frame_size, verbose=verbose)

    def on_start(self) -> None:
        """Initialize the VAD endpoint"""
        self._endpoint.on_start()
        
    def process(self, audio_packet: AudioPacket) -> None:
        assert isinstance(audio_packet, AudioPacket), f"Expected AudioPacket, got {type(audio_packet)}"
        if len(audio_packet) < self.frame_size:
            raise NotImplementedError("Partial audio packet found; this should not happen")
        self._endpoint.feed(audio_packet)

        # if self._endpoint.is_speaking():
        #     self.schedule_forward_interrupt()

        audio_packet_utterance = self._endpoint.get_utterance_if_any() 
        if audio_packet_utterance:
            # self.refresh()
            logger.debug(f"VADStage: Detected utterance of duration {audio_packet_utterance.duration}")
            self.pack(audio_packet_utterance)

    def reset_audio_stream(self) -> None:
        """Reset audio stream context"""
        self._endpoint.reset()

    # TODO use after some detection
    def refresh(self) -> None:
        """Refresh audio stream"""
        self.reset_audio_stream()

    def on_disconnect(self) -> None:
        self.reset_audio_stream()
