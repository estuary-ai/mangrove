import torch
from typing import Optional

from core.utils import logger
from core.stage import AudioToAudioStage
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

    def _process(self, audio_packet: AudioPacket) -> Optional[AudioPacket]:
        if audio_packet is None:
            return

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
