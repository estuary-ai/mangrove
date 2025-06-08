import torch
from typing import Union, List, Optional
from core import AudioPacket, AudioBuffer
from .base import VoiceActivityDetector

class SileroVAD(VoiceActivityDetector):
    def __init__(
        self,
        device: Optional[str] = None,
        is_speech_threshold: float = 0.85,
        head_silence_buffer_size: int = 200,
        tail_silence_threshold: int = 300,
        threshold_to_determine_speaking: int = 500,
        frame_size: int = 512 * 2,
        verbose: bool = False,
    ):
        if frame_size < 512 * 4:
            raise ValueError("Frame size must be at least 512*4 with Silero VAD")

        self.device = device
        if self.device is None:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        elif device.startswith('cuda'):
            self.device = "cuda:0"
        else:
            # because others are not guaranteed to work
            self.device = "cpu"

        self.is_speech_threshold = is_speech_threshold
        self.model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
        self.model: torch.nn.Module = self.model.eval()
        self.model.to(self.device)

        # (get_speech_timestamps,
        # save_audio,
        # read_audio,
        # VADIterator,
        # collect_chunks) = utils
        # vad_iterator = VADIterator(model)
        super().__init__(
            head_silence_buffer_size=head_silence_buffer_size,
            tail_silence_threshold=tail_silence_threshold, 
            threshold_to_determine_speaking=threshold_to_determine_speaking,
            frame_size=frame_size,
            verbose=verbose
        )

    def is_speech(self, audio_packets: Union[List[AudioPacket], AudioPacket]) -> Union[bool, List[bool]]:
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

        audio_buffer = AudioBuffer(self.frame_size)
        for audio_packet in audio_packets:
            audio_buffer.put(audio_packet)

        is_speeches = []
        for packet in audio_buffer:
            if len(packet) < self.frame_size:
                # partial TODO maybe add to buffer
                break
            _audio_tensor = torch.from_numpy(packet.float).to(self.device)
            is_speeches.append(
                self.model(_audio_tensor, packet.sample_rate) > self.is_speech_threshold
            )

        # if any([not is_speech for is_speech in is_speeches]):
        #     self.model.reset_states()

        if one_item:
            return is_speeches[0]
        return is_speeches

    def reset(self) -> None:
        super().reset()
        self.model.reset_states()
