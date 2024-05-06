import os
import pydub
import backoff
from pydub import AudioSegment
from loguru import logger
from typing import Generator, Dict
from abc import ABCMeta, abstractmethod

def get_mp3_audio_bytes(filepath='__temp__.mp3', chunk_size=1024) -> Generator[Dict, None, None]:
    # load mp3 file
    logger.debug(f"Loading mp3 file: {filepath}")
    @backoff.on_exception(backoff.expo, FileNotFoundError, max_tries=10)
    def load_mp3():
        return pydub.AudioSegment.from_mp3(filepath)
    audio = load_mp3()
    # delete the file
    os.remove(filepath)

    # chunk the audio
    for i in range(0, len(audio), chunk_size):
        yield {
            'audio_bytes': audio[i:i + chunk_size]._data,
            'frame_rate': audio.frame_rate,
            'sample_width': audio.sample_width,
            'channels': audio.channels
        }

def audio_segment_to_audio_bytes_dict(audio_segment: AudioSegment):
    return {
        'audio_bytes': audio_segment._data,
        'frame_rate': audio_segment.frame_rate,
        'sample_width': audio_segment.sample_width,
        'channels': audio_segment.channels
    }

class TTSEndpoint(metaclass=ABCMeta):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def text_to_audio_file(self, text, filepath):
        raise NotImplementedError()

    @abstractmethod
    def text_to_bytes(self, text) -> Generator[Dict, None, None]:
        raise NotImplementedError()