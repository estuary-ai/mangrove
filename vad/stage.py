import torch
from typing import Optional
from loguru import logger
from queue import Empty as QueueEmpty

from core.stage import AudioToAudioStage
from core import AudioPacket, AudioBuffer
from .endpoints.silero import SileroVAD


class VADStage(AudioToAudioStage):
    def __init__(
        self,
        silence_threshold=300,
        frame_size=512 * 4,
        device=None,
        verbose=False,
    ):
        super().__init__(frame_size=frame_size, verbose=verbose)

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        # self.endpoint = WebRTCVAD(vad_aggressiveness, silence_threshold, frame_size, verbose)
        self.endpoint = SileroVAD( 
            silence_threshold=silence_threshold,
            frame_size=frame_size,
            device=device,
            verbose=True,
        )

    def _process(self, audio_packet: AudioPacket) -> Optional[AudioPacket]:
        if audio_packet is None:
            return

        if len(audio_packet) < self.frame_size:
            raise Exception("Partial audio packet found; this should not happen")
        
        self.endpoint.feed(audio_packet)

        audio_packet_utterance = self.endpoint.get_utterance_if_any() 
        if audio_packet_utterance:
            # self.refresh()
            return audio_packet_utterance

    def reset_audio_stream(self) -> None:
        """Reset audio stream context"""
        self.endpoint.reset()

    # TODO use after some detection
    def refresh(self) -> None:
        """Refresh audio stream"""
        self.reset_audio_stream()

    def on_disconnect(self) -> None:
        self.reset_audio_stream()
