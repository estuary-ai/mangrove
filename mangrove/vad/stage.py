import torch
from typing import Optional

from core.utils import logger
from core.stage import AudioToAudioStage
from core import AudioPacket
from .endpoints.silero import SileroVAD


class VADStage(AudioToAudioStage):
    def __init__(
        self,
        is_speech_threshold=0.85,
        head_silence_buffer_size=200,
        tail_silence_threshold=300,
        interrupt_threshold=2000,
        frame_size=512 * 4,
        device=None,
        verbose=False,
    ):
        super().__init__(frame_size=frame_size, verbose=verbose)

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._endpoint = SileroVAD(
            is_speech_threshold=is_speech_threshold,
            head_silence_buffer_size=head_silence_buffer_size,
            tail_silence_threshold=tail_silence_threshold,
            threshold_to_determine_speaking=interrupt_threshold,
            frame_size=frame_size,
            device=device,
            verbose=verbose,
        )

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
