import time
import pyaudio
import numpy as np
from typing import List, Dict
from pydub import AudioSegment
from threading import Thread, Lock
from loguru import logger


class SoundManager:
    """Sound Manager class. Handles microphone stream and audio playback."""

    _self = None

    # Singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._self is None:
            cls._self = super().__new__(cls)
        return cls._self

    def __init__(
        self,
        stream_callback,
        _format=pyaudio.paFloat32,
        _channels=1,
        _sample_rate=16000,
        _frames_per_buffer=1024,
    ):
        """Constructor

        Args:
            stream_callback (function): callback function to be called when audio is received
            _format (pyaudio format, optional): pyaudio format. Defaults to pyaudio.paFloat32.
            _channels (int, optional): number of channels. Defaults to 1.
            _sample_rate (int, optional): sample rate. Defaults to 16000.
            _frames_per_buffer (int, optional): frames per buffer. Defaults to 1024., Where each byte corresponds to a sample of duration of 1/sample_rate seconds.

        Further explanation:
            _sample_rate: The number of samples per second. For example, 16000 means 16000 samples per second, meaning each sample corresponds to 1/16000 seconds.
            _frames_per_buffer: The number of samples per buffer. For example, 1024 means 1024 samples per buffer, meaning each buffer corresponds to 1024/16000 seconds = 64 milliseconds.
            _format: The format of the audio data. For example, pyaudio.paFloat32 means each sample is a float32 value.
            _channels: The number of audio channels. For example, 1 means mono audio, 2 means stereo audio.    
            _stream_callback: A callback function that will be called with the audio data when it is received. It gets called every time a new audio packet is available. which is approximately every 64 milliseconds (1024 samples at 16000 Hz sample rate).
        """
        self._format = _format
        self._channels = _channels
        self._sample_rate = _sample_rate
        self._frames_per_buffer = _frames_per_buffer
        self._DEBUG_last_packet_details: Dict = None
        self.stream = None
        self.stream_callback = stream_callback
        self.threads_pool: List[Thread] = []
        self._audio = pyaudio.PyAudio()
        self._lock = Lock()
        self._offset = 0

    def open_mic(self):
        """Opens the microphone stream"""
        self._mic_stream = self._audio.open(
            format=self._format,
            channels=self._channels,
            rate=self._sample_rate,
            input=True,
            input_device_index=1,
            stream_callback=self.callback_pyaudio,
            frames_per_buffer=self._frames_per_buffer,
        )

    def open_speaker(self, sample_rate, sample_width, channels):
        """Opens the speaker stream"""
        _format = pyaudio.get_format_from_width(sample_width)
        if hasattr(self, "_speaker_stream") and self._speaker_stream is not None:
            # is setup the same parameters
            if (
                self._speaker_stream._format == _format
                and self._speaker_stream._channels == channels
                and self._speaker_stream._rate == sample_rate
            ):
                return
            self._speaker_stream.stop_stream()
            self._speaker_stream.close()
        self._speaker_stream = self._audio.open(
            format=_format,
            channels=channels,
            rate=sample_rate,
            output=True,
        )

    # def callback(self, indata, frames, time, status):
    #     """ This is called (from a separate thread) for each audio block.

    #     Args:
    #         indata (numpy.ndarray): audio data
    #         frames (int): number of frames
    #         time (CData): time
    #         status (CData): status
    #     """
    #     self.stream_callback({
    #         "audio": list(indata.flatten().astype(float)),
    #         "numChannels": 1,
    #         "sampleRate": self._rate,
    #         "timestamp": int(time.time()*1000)
    #     })

    def callback_pyaudio(self, audio_bytes, frame_count, time_info, flags):
        """This is called (from a separate thread) for each audio block."""

        audio_float32 = np.fromstring(audio_bytes, np.float32).astype(float)
        # audio_int16 = np.fromstring(audio_bytes, np.int16).astype(float)
        timestamp = int(time.time() * 1000)  # current timestamp in milliseconds
        duration_ms = (frame_count / self._sample_rate) * 1000  # duration in milliseconds

        self.stream_callback(
            {
                "audio": list(audio_float32),
                "numChannels": 1,
                "sampleRate": self._sample_rate,
                "timestamp": timestamp,
                "sampleWidth": 4,  # "format": "f32le", # float32
                # "format": "s16le", # int16
            }
        )
        # if self._DEBUG_last_packet_details is not None:
        #     _last_timestamp = self._DEBUG_last_packet_details['timestamp']
        #     _last_duration = self._DEBUG_last_packet_details['duration']
        #     _last_timestamp_end = _last_timestamp + _last_duration
        #     if timestamp - _last_timestamp_end > 0:
        #         logger.warning(
        #             f"Audio packet received with timestamp {timestamp} ms, "
        #             f"but last packet ended at {_last_timestamp_end} ms. "
        #             f"DIFFERENCE: {timestamp - _last_timestamp_end} ms"
        #         )
                
        # self._DEBUG_last_packet_details = {
        #     "timestamp": timestamp,
        #     "duration": duration_ms,
        #  }

        return audio_bytes, pyaudio.paContinue

    def close_mic(self):
        """Closes the microphone stream"""
        if self._mic_stream and self._mic_stream.is_active:
            self._mic_stream.stop_stream()
            self._mic_stream.close()

    def _enqueue_task(self, func, *args):
        """Enqueues a task to be executed in a thread

        Args:
            func (function): function to be executed
            *args: arguments to be passed to function
        """
        thread = Thread(target=func, args=args, daemon=True)
        thread.name = f"SoundManagerThread-{len(self.threads_pool)}"
        thread.start()
        self.threads_pool.append(thread)

    def interrupt(self, timestamp):
        """Interrupts the audio playback by setting the offset to the timestamp"""
        self._offset = timestamp

    def play_audio_packet(self, audio_packet, block=True):
        """Plays audio bytes

        Args:
            audio (bytes or str): audio bytes or filepath to audio bytes
            block (bool, optional): if True, blocks until audio is played. Defaults to False.
        """
        def _play_packet(audio_packet):
            with self._lock:
                # divide audio into chunks
                for i in range(0, len(audio_packet['bytes']), self._frames_per_buffer):
                    if audio_packet['timestamp'] < self._offset:
                        logger.warning("Skipping audio packet as it is interrupted")
                        break

                    print('>', end='')
                    audio_bytes = audio_packet['bytes'][i : i + self._frames_per_buffer]
                    sample_rate = audio_packet['sampleRate']
                    sample_width = audio_packet['sampleWidth']
                    num_channels = audio_packet['numChannels']
                    # play audio
                    self.open_speaker(sample_rate, sample_width, num_channels)
                    self._speaker_stream.write(audio_bytes)

        if block:
            _play_packet(audio_packet)
        else:
            self._enqueue_task(_play_packet, audio_packet)

    def play_audio_file(self, filepath, format, block=False):
        audio = AudioSegment.from_file(filepath, format=format)
        self.play_audio_packet(
            {
                "bytes": audio.raw_data,
                "sampleRate": audio.frame_rate,
                "sampleWidth": audio.sample_width,
                "numChannels": audio.channels,
            },
            block=True,
        )

    def play_activation_sound(self):
        """Plays activation sound"""
        self.play_audio_file("assistant_activate.wav", format="wav", block=True)


    def play_termination_sound(self):
        """Plays termination sound"""
        self.play_audio_file("assistant_terminate.mp3", format="mp3", block=True)