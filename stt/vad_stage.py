import torch
from typing import Optional
from loguru import logger

from core.stage import AudioToAudioStage
from core import AudioPacket, AudioBuffer
from .vad.silero import SileroVAD

class VADStage(AudioToAudioStage):
    def __init__(
        self,
        silence_threshold=700,
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

        self._command_audio_packet = None

        # TODO make them in one debug variable
        self.debug_silence_size = 0
        self.debug_voice_size = 0


    def _process(self, audio_packet: AudioPacket) -> Optional[AudioPacket]:
        if audio_packet is None:
            return

        if len(audio_packet) < self.frame_size:
            # partial TODO maybe add to buffer
            logger.error(f"Partial audio packet found: {len(audio_packet)}")
            raise Exception("Partial audio packet found")

        is_speech = self.endpoint.is_speech(audio_packet)
        if is_speech:
            self.debug_voice_size += len(audio_packet) # For DEBUGGING

            frame_inc_silence = self.endpoint.process_voice(audio_packet)
            if self._command_audio_packet is None: # first voice frame
                self._command_audio_packet = audio_packet
                logger.success(f"Starting an utterance AudioPacket at {audio_packet.timestamp}")
            else:
                self._command_audio_packet += audio_packet

        else:
            self.debug_silence_size += len(audio_packet) # For DEBUGGING

            # Process silence frame and finish stream if silence threshold is reached
            if self.endpoint.detected_silence_after_voice(audio_packet):  # recording after some voice
                # self.log('-') # silence detected while recording
                # TODO Add to buffer until silence surpasses threshold
                self._command_audio_packet += audio_packet
                if self.endpoint.is_silence_cross_threshold(audio_packet):
                    # Returns decoding in JSON format and reinit the stream
                    # Transcription if any found and stream finished while silence threshold is reached
                    # TODO return whole buffer instead of audio_packet
                    to_return = self._command_audio_packet
                    self._command_audio_packet = None
                    self.refresh()
                    return to_return

    
    def reset_audio_stream(self) -> None:
        """Reset audio stream context"""
        self.endpoint.reset()
        self._command_audio_packet = None
        self.debug_silence_size = 0
        self.debug_voice_size = 0

    # TODO use after some detection
    def refresh(self) -> None:
        """Refresh audio stream"""
        self.reset_audio_stream()

    def on_disconnect(self) -> None:
        self.reset_audio_stream()
