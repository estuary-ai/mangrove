import webrtcvad
from typing import Union, List
from core import AudioPacket
from .base import VoiceActivityDetector

class WebRTCVAD(VoiceActivityDetector):

    def __init__(
        self,
        aggressiveness: int = 3,
        silence_threshold: int = 200,
        frame_size: int = 320 * 3,
        verbose=False,
    ):
        if frame_size not in [320, 640, 960]:
            raise ValueError("Frame size must be 320, 640 or 960 with WebRTC VAD")
        self.aggressiveness = aggressiveness
        self.model = webrtcvad.Vad(aggressiveness)
        super().__init__(silence_threshold, frame_size, verbose)

    def is_speech(self, audio_packets: Union[List[AudioPacket], AudioPacket]):
        """Check if audio is speech

        Args:
            audio_packet (AudioPacket): Audio packet to check

        Returns:
            bool: True if speech, False otherwise
        """
        one_item = False
        if not isinstance(audio_packets, list):
            audio_packets = [audio_packets]
            one_item = True

        is_speeches = []
        for packet in audio_packets:
            if len(packet) < self.frame_size:
                # partial TODO maybe add to buffer
                break
            audio_bytes, sample_rate = packet.bytes, packet.sample_rate
            is_speeches.append(self.model.is_speech(audio_bytes, sample_rate))

        # if any([not is_speech for is_speech in is_speeches]):
        #     self.model = webrtcvad.Vad(self.aggressiveness)

        if one_item:
            return is_speeches[0]
        return is_speeches

    def reset(self):
        super().reset()
        self.model = webrtcvad.Vad(self.aggressiveness)