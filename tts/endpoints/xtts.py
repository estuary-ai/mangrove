import io
import os
import time
import scipy
import torch
import numpy as np
from typing import Generator
from TTS.tts.configs.xtts_config import XttsConfig, XttsAudioConfig
from TTS.tts.models.xtts import Xtts
from TTS.api import TTS
from pydub import AudioSegment
from loguru import logger
from core.data import AudioPacket
from core.utils import np_audio_to_audio_packet
from .elevenlabs import ElevenLabsTTSEndpoint
from .base import TTSEndpoint

class TTSLibraryEndpoint(TTSEndpoint):
    def __init__(
        self,
        model_name="tts_models/multilingual/multi-dataset/xtts_v2",
        device=None,
        **kwargs
    ):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        ckpt_dir = TTS().download_model_by_name(model_name)[-1]
        config_path = os.path.join(ckpt_dir, "config.json")
        if not os.path.exists(config_path):
            raise ValueError(f"Config file not found at {config_path}")

        config = XttsConfig()
        config.load_json(config_path)
        model: Xtts = Xtts.init_from_config(config)
        model.load_checkpoint(config, checkpoint_dir=ckpt_dir, use_deepspeed=True)
        if device == "cuda":
            model.cuda()
        self._ensure_speaker_wav()
        logger.info("Computing speaker latents of xTTS model")
        self.gpt_cond_latent, self.speaker_embedding = model.get_conditioning_latents(audio_path=["speaker.wav"])
        self.model = model
        self.sample_rate = XttsAudioConfig.output_sample_rate

    def _ensure_speaker_wav(self) -> None:
        if not os.path.exists('speaker.wav'):
            # generate speaker.wav using ElevenLabsTTSEndpoint
            logger.warning("Generating speaker.wav using ElevenLabsTTSEndpoint as it is not available.")
            ElevenLabsTTSEndpoint().text_to_audio_file(
                "Hello, I am your assistant. I am here to help you with your tasks."
                "I am a digital assistant created by the Estuary team. I am here to help you with your tasks.",
                'speaker.wav'
            )

    def text_to_audio_file(self, text, filepath) -> None:
        raise NotImplementedError("This method is not implemented for TTSLibraryEndpoint")
    #     self.engine.tts_to_file(text=text, file_path=filepath, speaker_wav="speaker.wav", language="en")

    def text_to_audio(self, text) -> Generator[AudioPacket, None, None]:
        t0 = time.time()
        chunks = self.model.inference_stream(
            text,
            language="en",
            gpt_cond_latent=self.gpt_cond_latent,
            speaker_embedding=self.speaker_embedding,
            stream_chunk_size=500,
            enable_text_splitting=True,
        )

        for i, chunk in enumerate(chunks):
            # if i == 0:
            #     print(f"Time to first chunck: {time.time() - t0}")
            # print(f"Received chunk {i} of audio length {chunk.shape[-1]}")
            yield np_audio_to_audio_packet(chunk.cpu().numpy(), self.sample_rate)

