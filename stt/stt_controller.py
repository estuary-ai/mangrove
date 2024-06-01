import time
from threading import Lock
from loguru import logger
from storage_manager import StorageManager
from multiprocessing import JoinableQueue
from queue import Empty, Full
from .data_buffer import DataBuffer
from .audio_packet import AudioPacket
from .vad_detector import SileroVAD
from .stt_endpoints import WhisperEndpoint


class STTController:
    """Speech to Text Controller"""

    def __init__(
        self,
        silence_threshold=300,
        # vad_aggressiveness=1,
        # frame_size=320*3,
        frame_size=512 * 4,
        device=None,
        verbose=False,
    ):
        """Initialize STT Controller

        Args:
            sample_rate (int, optional): Sample rate. Defaults to 16000.
            silence_threshold (int, optional): Silence threshold. Defaults to 200 ms.
            vad_aggressiveness (int, optional): VAD aggressiveness. Defaults to 3.
            frame_size (int, optional): Speech frame size. Defaults to 320.
            verbose (bool, optional): Whether to print debug messages. Defaults to False.

        Raises:
            ValueError: If custom scorer is defined but not found
        """

        import torch
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.verbose = verbose
        self.frame_size = frame_size
        self._input_buffer = DataBuffer(self.frame_size)
        self._output_buffer = JoinableQueue()

        # self.vad = WebRTCVoiceActivityDetector(vad_aggressiveness, silence_threshold, frame_size, verbose)
        self.vad = SileroVAD(
            silence_threshold=silence_threshold,
            frame_size=frame_size,
            device=device,
            verbose=verbose,
        )
        self.model = WhisperEndpoint(device=device)

        self.debug_total_size = 0
        self.debug_silence_size = 0
        self.debug_voice_size = 0
        self.caught_voice = False

        self._lock = Lock()

    def start(self, server):
        """Start STT Controller Thread"""
        def _start_thread():
            while True:
                stt_res = self.process_audio_buffer()
                if stt_res is None:
                    server.sleep(0.1)
                    # print('<stt>', end='', flush=True)
                else:
                    self._output_buffer.put(stt_res)

        self._process = server.start_background_task(_start_thread)

    def receive(self):
        """Get transcription from STT Controller"""
        outputs = []
        try:
            while True:
                outputs.append(self._output_buffer.get_nowait())
        except Empty:
            pass
        if len(outputs) > 0:
            return self._combine_outcomes(outputs)
        return None

    def create_stream(self):
        """Create a new stream context"""
        self.model.create_stream()
        ##### DEBUG #####
        self.recorded_audio_length = 0
        logger.warning("Reset debug feed frames")
        self.debug_feed_frames = AudioPacket.get_null_packet()

    def _finish_stream(self, force_clear_buffer=False):
        """Finish stream and return transcription if any found"""
        logger.debug("Trying to finish stream..")
        time_start_recog = round(time.time() * 1000)

        if force_clear_buffer:
            # feed all remaining audio packets to stream context
            self.process_audio_buffer()

        transcription = self.model.get_transcription()
        # transcription = self.stream_context.intermediateDecode()
        # CONFIDENCE_THRESHOLD = 0
        # valid_transcripts = [t for t in transcription.transcripts if t.confidence > CONFIDENCE_THRESHOLD]
        if transcription:
            # StorageManager.play_audio_packet(self.debug_feed_frames, transcription) # TODO Remove if not debugging

            self._log(f"Recognized Text: {transcription}", end="\n")
            recog_time = round(time.time() * 1000) - time_start_recog
            result = {
                "text": transcription,
                "recog_time": recog_time,
                "recorded_audio_length": self.recorded_audio_length,
            }
            self.refresh()
            return result

        # with open(f'../sample-audio-binary/null_{str(time.time())}.txt', mode="wb") as f:
        #     f.write(self.debug_feed_frames)

    def _feed_audio_content(self, audio_packet: AudioPacket):
        """Feed audio content to stream context

        Args:
            audio_packet (AudioPacket): Audio packet of voice frame
        """
        self.model.buffer_audio_packet(audio_packet)

        ##### DEBUG #####
        self.recorded_audio_length += audio_packet.duration
        self.debug_feed_frames += audio_packet

    def _process_voice(self, frame: AudioPacket):
        """Process voice frame and feed to stream context

        Args:
            frame (AudioPacket): Audio packet of voice frame
        """
        frame_inc_silence = self.vad.process_voice(frame)
        self._feed_audio_content(frame_inc_silence)

    # TODO make _process_silence using samples count or percentge instead of time
    def _process_silence(self, frame: AudioPacket):
        """Process silence frame and finish stream if silence threshold is reached

        Args:
            frame (AudioPacket): Audio packet of silence frame

        Returns:
            dict: Transcription if any found and stream finished while silence threshold is reached
        """
        if self.vad.detected_silence_after_voice(frame):  # recording after some voice
            # self._log('-') # silence detected while recording
            self._feed_audio_content(frame)
            if self.vad.is_silence_cross_threshold(frame):
                # Returns decoding in JSON format and reinit the stream
                results = self._finish_stream()
                # TODO move create_stream()
                self.create_stream()
                return results
        # else:
        #     # self._log('.') # silence detected while not recording
        #     print(f'-------- Silence before voice at {frame.timestamp}')

    def feed(self, audio_packet: AudioPacket):
        """Feed audio packet to STT Controller

        Args:
            audio_packet (AudioPacket): Audio packet to feed
        """
        self._input_buffer.put(audio_packet)

    def process_audio_buffer(self):
        with self._lock:
            return self._process_audio_buffer()

    def _process_audio_buffer(self):
        """Process audio buffer and return transcription if any found"""
        outcomes = []
        # Process only proper frame sizes
        debug_num_packets = 0

        audio_packets = []
        while True:
            try:
                audio_packet = self._input_buffer.get(self.frame_size, timeout=-1)
                audio_packets.append(audio_packet)
            except DataBuffer.Empty:
                if len(audio_packets) == 0:
                    # logger.warning('No audio packets found in buffer', flush=True)
                    return
                break

        # NOTE: all packets that were able to get are combined in one here!
        audio_packets = [sum(audio_packets, AudioPacket.get_null_packet())]
        for audio_packet in audio_packets:
            if len(audio_packet) < self.frame_size:
                # partial TODO maybe add to buffer
                break

            is_speech = self.vad.is_speech(audio_packet)

            if is_speech:
                self._process_voice(audio_packet)
                if not self.caught_voice:
                    self.caught_voice = True
                    logger.success(
                        f"caught voice for the first time at {audio_packet.timestamp}"
                    )
            else:
                # print('Silence')
                result = self._process_silence(audio_packet)
                if result is not None:
                    self.caught_voice = False
                    outcomes.append(result)
                # else:
                #     print('no result as Silence before some voice')

            ##### DEBUG #####
            debug_num_packets += 1
            self.debug_total_size += len(audio_packet)
            if is_speech:
                self.debug_voice_size += len(audio_packet)
            else:
                self.debug_silence_size += len(audio_packet)

        if len(outcomes) > 0:
            return self._combine_outcomes(outcomes)

    def _combine_outcomes(self, outcomes):
        """Combine outcomes of multiple segments into one

        Args:
            outcomes (list): List of outcomes (transcriptions)

        Returns:
            dict: Merged outcome
        """

        def _gen_base_case(value):
            if isinstance(value, str):
                return ""
            elif isinstance(value, bytes):
                return b""
            elif isinstance(value, (float, int)):
                return 0
            elif isinstance(value, dict):
                _base = {}
                for key, value in value.items():
                    _base[key] = _gen_base_case(value)
                return _base
            else:
                raise TypeError(f"Unknown type {type(value)}")

        merged_outcome = {
            key: _gen_base_case(value) for key, value in outcomes[0].items()
        }

        for outcome in outcomes:
            for key, value in outcome.items():
                if isinstance(value, str):
                    merged_outcome[key] += value.strip()
                elif isinstance(value, dict):
                    for _key, _value in value.items():
                        merged_outcome[key][_key] += _value
                else:
                    merged_outcome[key] += value
        return merged_outcome

    def reset_audio_stream(self):
        """Reset audio stream context"""
        self._log("[reset]", end="\n")
        self.create_stream()
        self._input_buffer.reset()
        self.model.reset()
        self.vad.reset()

    # TODO use after some detection
    def refresh(self):
        """Refresh STT Controller"""
        # self._log('[refresh]', end='\n')
        # self.reset_audio_stream()
        self.vad.reset()

    def _log(self, msg, end="", force=False):
        """Log message to console if verbose is True or force is True with flush

        Args:
            msg (str): Message to log
            end (str, optional): End character. Defaults to "".
            force (bool, optional): Force logging. Defaults to False.

        """
        if self.verbose or force:
            print(msg, end=end, flush=True)
