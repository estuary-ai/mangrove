import time
from loguru import logger
from core import AudioPacket, TextPacket, AudioBuffer
from core.stage import AudioToTextStage
from .vad.silero import SileroVAD
from .endpoints.faster_whisper import FasterWhisperEndpoint

class STTController(AudioToTextStage):
    """Speech to Text Controller"""

    def __init__(
        self,
        silence_threshold=300,
        frame_size=512 * 4,
        device=None,
        verbose=False,
    ):
        """Initialize STT Controller

        Args:
            sample_rate (int, optional): Sample rate. Defaults to 16000.
            silence_threshold (int, optional): Silence threshold. Defaults to 200 ms.
            frame_size (int, optional): audio frame size. Defaults to 320.
            device (str, optional): Device to use. Defaults to None.
            verbose (bool, optional): Whether to print debug messages. Defaults to False.

        Raises:
            ValueError: If custom scorer is defined but not found
        """
        super().__init__(frame_size=frame_size, verbose=verbose)

        import torch
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        # self.vad = WebRTCVAD(vad_aggressiveness, silence_threshold, frame_size, verbose)
        self.vad = SileroVAD(
            silence_threshold=silence_threshold,
            frame_size=frame_size,
            device=device,
            verbose=verbose,
        )
        self.model = FasterWhisperEndpoint(device=device)

        self.debug_total_size = 0
        self.debug_silence_size = 0
        self.debug_voice_size = 0
        self.caught_voice = False
        self._command_audio_buffer = AudioBuffer(frame_size=frame_size)

    def on_start(self):
        self._create_stream()

    def on_sleep(self):
        self.log('<stt>')

    def _create_stream(self):
        """Create a new stream context"""
        self.model.create_stream()

        ##### DEBUG #####
        self.recorded_audio_length = 0
        logger.warning("Reset debug feed frames")

    # def feed(self, audio_packet: AudioPacket):
    #     """Feed audio packet to STT Controller

    #     Args:
    #         audio_packet (AudioPacket): Audio packet to feed
    #     """
    #     # if self._command_audio_buffer.is_empty():
    #     #     self._create_stream()
    #     #     self.log("receiving first stream of audio command")
    #     self._input_buffer.put(audio_packet)

    def _feed_audio_content(self, audio_packet: AudioPacket):
        """Feed audio content to stream context

        Args:
            audio_packet (AudioPacket): Audio packet of voice frame
        """
        self.model.buffer_audio_packet(audio_packet)

        ##### DEBUG #####
        self.recorded_audio_length += audio_packet.duration

    def _process(self, audio_packet):
        """Process audio buffer and return transcription if any found"""
        def _process_voice(frame: AudioPacket):
            """Process voice frame and feed to stream context

            Args:
                frame (AudioPacket): Audio packet of voice frame
            """
            frame_inc_silence = self.vad.process_voice(frame)
            self._feed_audio_content(frame_inc_silence)

        # TODO make _process_silence using samples count or percentge instead of time
        def _process_silence(frame: AudioPacket):
            """Process silence frame and finish stream if silence threshold is reached

            Args:
                frame (AudioPacket): Audio packet of silence frame

            Returns:
                dict: Transcription if any found and stream finished while silence threshold is reached
            """
            def _finish_stream():
                """Finish stream and return transcription if any found"""
                logger.debug("Trying to finish stream..")
                time_start_recog = round(time.time() * 1000)

                # if force_clear_buffer:
                #     # TODO look into this
                #     # feed all remaining audio packets to stream context
                #     self._process(self._unpack())

                transcription = self.model.get_transcription()
                if transcription:
                    self.log(f"Recognized Text: {transcription}", end="\n")
                    recog_time = round(time.time() * 1000) - time_start_recog
                    self.refresh()

                    return TextPacket(
                        text=transcription,
                        partial=False,
                        start=True,
                        recog_time=recog_time,
                        recorded_audio_length=self.recorded_audio_length,
                    )


            if self.vad.detected_silence_after_voice(frame):  # recording after some voice
                # self.log('-') # silence detected while recording
                self._feed_audio_content(frame)
                if self.vad.is_silence_cross_threshold(frame):
                    # Returns decoding in JSON format and reinit the stream
                    result = _finish_stream()
                    # TODO move create_stream()
                    self._create_stream()
                    return result
            # else:
            #     # self.log('.') # silence detected while not recording
            #     print(f'-------- Silence before voice at {frame.timestamp}')

        if audio_packet is None:
            return

        if len(audio_packet) < self.frame_size:
            # partial TODO maybe add to buffer
            logger.error(f"Partial audio packet found: {len(audio_packet)}")
            raise Exception("Partial audio packet found")

        self.debug_total_size += len(audio_packet) # For DEBUGGING

        is_speech = self.vad.is_speech(audio_packet)
        if is_speech:
            self.debug_voice_size += len(audio_packet) # For DEBUGGING

            _process_voice(audio_packet)
            if not self.caught_voice:
                self.caught_voice = True
                logger.success(
                    f"caught voice for the first time at {audio_packet.timestamp}"
                )

        else:
            self.debug_silence_size += len(audio_packet) # For DEBUGGING

            result = _process_silence(audio_packet)
            if result is not None:
                self.caught_voice = False

            return result


    def reset_audio_stream(self):
        """Reset audio stream context"""
        self.log("[reset]", end="\n")
        if not self._command_audio_buffer.is_empty():
            from storage_manager import StorageManager
            StorageManager.play_audio_packet(self._command_audio_buffer)

        self._create_stream()
        self._input_buffer.reset()
        self._command_audio_buffer.reset()
        self.model.reset()
        self.vad.reset()

    # TODO use after some detection
    def refresh(self):
        """Refresh STT Controller"""
        # self.log('[refresh]', end='\n')
        # self.reset_audio_stream()
        self.vad.reset()


    def on_disconnect(self):
        self.reset_audio_stream()
        self.log("[disconnect]", end="\n")