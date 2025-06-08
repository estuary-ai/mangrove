import io
import os
import time
import scipy
import pydub
import backoff
import numpy as np
from pydub import AudioSegment
from typing import Generator
from core import AudioPacket

# TODO adjust automatically a sort of universal target_sample_rate according to client's perference!
TARGET_SAMPLE_RATE = 48000

def filepath_to_audio_packet(
    filepath: str='__temp__.mp3', 
    chunk_size: int=1024,
    remove_after: bool=False,
    max_tries: int=10,
    target_sample_rate: int=TARGET_SAMPLE_RATE
) -> Generator[AudioPacket, None, None]:
    # load mp3 file
    # logger.debug(f"Loading mp3 file: {filepath}")
    @backoff.on_exception(backoff.expo, FileNotFoundError, max_tries=max_tries)
    def load_mp3():
        return pydub.AudioSegment.from_mp3(filepath)
    audio = load_mp3()
    # delete the file
    if remove_after:
        os.remove(filepath)

    # chunk the audio
    last_packet_timestamp = time.time() * 1000  # current timestamp in milliseconds
    num_chunks = len(audio) // chunk_size + (1 if len(audio) % chunk_size > 0 else 0)
    # generate timestamps for each chunk (going back in time)
    simulated_timestamps = list(reversed([
        last_packet_timestamp - (i * chunk_size) for i in range(num_chunks)
    ]))
    timestamps_idx = 0
    for i in range(0, len(audio), chunk_size):
        yield AudioPacket({
                'timestamp': int(simulated_timestamps[timestamps_idx]),
                'bytes': audio[i:i + chunk_size]._data,
                'sampleRate': audio.frame_rate,
                'sampleWidth': audio.sample_width,
                'numChannels': audio.channels,
            }, resample=True, is_processed=False, 
            target_sample_rate=target_sample_rate
        )
        timestamps_idx += 1

def pydub_audio_segment_to_audio_packet(
        audio_segment: AudioSegment,
        target_sample_rate: int=TARGET_SAMPLE_RATE
    ) -> AudioPacket:
    return AudioPacket({
            'bytes': audio_segment._data,
            'sampleRate': audio_segment.frame_rate,
            'sampleWidth': audio_segment.sample_width,
            'numChannels': audio_segment.channels,
        }, resample=True, is_processed=False, 
        target_sample_rate=target_sample_rate
    )

def np_audio_to_audio_segment(wav_audio: np.ndarray, sample_rate: int):
    wav_norm = wav_audio * (32767 / max(0.01, np.max(np.abs(wav_audio))))
    wav_norm = wav_norm.astype(np.int16)
    wav_buffer = io.BytesIO()
    scipy.io.wavfile.write(wav_buffer, sample_rate, wav_norm)
    wav_buffer.seek(0)
    return AudioSegment.from_file(wav_buffer, format="wav")

def np_audio_to_audio_packet(wav_audio: np.ndarray, sample_rate: int):
    return pydub_audio_segment_to_audio_packet(
        np_audio_to_audio_segment(wav_audio, sample_rate)
    )

def bytes_to_audio_packet(audio_bytes: bytes, format=None) -> AudioPacket:
    # convert bytes to audio segment
    audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=format)
    return pydub_audio_segment_to_audio_packet(audio_segment)