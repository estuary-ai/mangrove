import time
import pyaudio
import numpy as np
import sounddevice as sd
from playsound import playsound
from threading import Thread


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
            _frames_per_buffer (int, optional): frames per buffer. Defaults to 1024.
        """
        self._format = _format
        self._channels = _channels
        self._sample_rate = _sample_rate
        self._frames_per_buffer = _frames_per_buffer
        self.stream = None
        self.stream_callback = stream_callback
        self.threads_pool = []
        self.audio = pyaudio.PyAudio()

    def open_mic(self):
        """Opens the microphone stream"""
        self.mic_stream = self.audio.open(
            format=self._format,
            channels=self._channels,
            rate=self._sample_rate,
            input=True,
            stream_callback=self.callback_pyaudio,
            frames_per_buffer=self._frames_per_buffer,
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

        self.stream_callback(
            {
                "audio": list(audio_float32),
                "numChannels": 1,
                "sampleRate": self._sample_rate,
                "timestamp": int(time.time() * 1000),
                # "format": "s16le", # int16
            }
        )
        return audio_bytes, pyaudio.paContinue

    def close_mic(self):
        """Closes the microphone stream"""
        if self.mic_stream and self.mic_stream.is_active:
            self.mic_stream.stop_stream()
            self.mic_stream.close()

    def _enqueue_task(self, func, *args):
        """Enqueues a task to be executed in a thread

        Args:
            func (function): function to be executed
            *args: arguments to be passed to function
        """
        thread = Thread(target=func, args=args)
        thread.start()
        self.threads_pool.append(thread)

    def play_audio_packet(self, audio, sample_rate=20000, block=False):
        """Plays audio bytes

        Args:
            audio (bytes or str): audio bytes or filepath to audio bytes
            block (bool, optional): if True, blocks until audio is played. Defaults to False.
        """

        def play_packet(audio, sample_rate):
            def save_audio_bytes_as_wav(audio, sample_rate):
                """Saves audio bytes as wav file"""
                with open("audio.wav", "wb") as f:
                    f.write(audio)


            if isinstance(audio, str):
                # It is filepath hopefully
                playsound(audio)
            else:
                # try:
                #     sd.play(np.frombuffer(audio, dtype=np.int16), sample_rate)
                #     sd.wait()
                # except:
                print('Error playing audio, saving as wav file, and playing it')
                save_audio_bytes_as_wav(audio, sample_rate)
                playsound("audio.wav")


        if block:
            play_packet(audio)
        else:
            self._enqueue_task(play_packet, audio, sample_rate)

    def play_activation_sound(self):
        """Plays activation sound"""
        self.play_audio_packet("assistant_activate.wav", sample_rate=16000)

    def play_termination_sound(self):
        """Plays termination sound"""
        self.play_audio_packet("assistant_terminate.mp3", sample_rate=16000)
