import torch
from typing import Optional
from loguru import logger

from core.stage import AudioToAudioStage
from core import AudioPacket
from .endpoints.silero import SileroVAD


class VADStage(AudioToAudioStage):
    def __init__(
        self,
        is_speech_threshold=0.85,
        tail_silence_threshold=350,
        frame_size=512 * 4,
        device=None,
        verbose=False,
    ):
        super().__init__(frame_size=frame_size, verbose=verbose)

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.endpoint = SileroVAD( 
            is_speech_threshold=is_speech_threshold,
            tail_silence_threshold=tail_silence_threshold,
            frame_size=frame_size,
            device=device,
            verbose=verbose,
        )

    def _process(self, audio_packet: AudioPacket) -> Optional[AudioPacket]:
        if audio_packet is None:
            return

        if len(audio_packet) < self.frame_size:
            raise Exception("Partial audio packet found; this should not happen")
        
        self.endpoint.feed(audio_packet)

        if self.endpoint.is_speaking(threshold=200): # TODO make this a parameter 
            self.signal_interrupt()

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
