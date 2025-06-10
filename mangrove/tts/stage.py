from string import punctuation
from typing import Generator, Union, List
from itertools import chain
from functools import reduce

from core.utils import logger
from core.data import AudioPacket, TextPacket
from core.stage import TextToAudioStage
from core.stage.base import SequenceMismatchException, QueueEmpty
from .endpoints.base import TTSEndpoint


class TTSStage(TextToAudioStage):
    """Text to speech Stage"""

    input_type = TextPacket
    output_type = AudioPacket

    def __init__(
        self,
        endpoint="pyttsx3",
        endpoint_kwargs={
            "voice_rate": 140,
            "voice_id": 10,
        },
        verbose=False,
    ):
        super().__init__(verbose=verbose)
        self.endpoint: TTSEndpoint
        # TODO select in dynamic cleaner way
        if endpoint == "pyttsx3":
            logger.info("Using Pyttsx3 TTS Endpoint")
            from .endpoints.pyttsx3 import Pyttsx3TTSEndpoint
            self.endpoint = Pyttsx3TTSEndpoint(**endpoint_kwargs)
        elif endpoint == "xtts":
            from .endpoints.xtts import TTSLibraryEndpoint
            self.endpoint = TTSLibraryEndpoint()
        elif endpoint == "elevenlabs":
            from .endpoints.elevenlabs import ElevenLabsTTSEndpoint
            logger.info("Using ElevenLabs TTS Endpoint")
            self.endpoint = ElevenLabsTTSEndpoint()
        elif endpoint == "gtts":
            from .endpoints.gtts import GTTSEndpoint
            logger.info("Using GTTS TTS Endpoint")
            self.endpoint = GTTSEndpoint()
        else:
            raise Exception(f"Unknown Endpoint {endpoint}, available endpoints: pyttsx3, tts")

        self._sentence_text_packet = None
        self._audiopacket_generator: Generator[AudioPacket, None, None] = None
        self._generated_audio_packet_per_sentence_count = 0

        self.debug = False


    def _process(self, in_text_packet: TextPacket):
        # accepts a stream of text packets
        # upon completion of a sentence (detection component), a stream is yielded
        # sends a stream of audio packets

        def _process_sentence_text_packet():
            _new_audiopacket_generator = self.endpoint.text_to_audio(
                self._sentence_text_packet
            )
            if self._audiopacket_generator is not None:
                self._audiopacket_generator = chain(
                    self._audiopacket_generator,
                    _new_audiopacket_generator
                )
            else:
                self._audiopacket_generator = _new_audiopacket_generator

            # NOTE: reset complete_segment because you got a complete response
            self._sentence_text_packet = None

        if in_text_packet is None and self._audiopacket_generator is None:
            return None

        if in_text_packet:
            logger.success(f"Processing: {in_text_packet}")
            if in_text_packet.partial:
                self.log(f"{in_text_packet.text}")

                if self._sentence_text_packet is None:
                    if in_text_packet.start:
                        self._generated_audio_packet_per_sentence_count = 0
                        self.log("SENVA: ")
                    # implement SentenceTextDataBuffer
                    self._sentence_text_packet: TextPacket = in_text_packet
                else:
                    if in_text_packet.start:
                        self._sentence_text_packet = in_text_packet
                        self.schedule_forward_interrupt()
                        # TODO investigate this
                        logger.error(f"Partial response should not have start: {in_text_packet}, interrupting and starting new")
                    else:
                        self._sentence_text_packet += in_text_packet

                if self._sentence_text_packet.text.endswith(('?', '!', '.')):
                    # TODO prompt engineer '.' and check other options
                    _process_sentence_text_packet()

            else:
                # NOTE: _process leftover sentence_text_packet if any
                if self._sentence_text_packet is not None:
                    if len(self._sentence_text_packet.text.replace(punctuation, '').strip()) > 0:
                        # assert not self._sentence_text_packet.partial, "Partial should be False" # NOTE: this is the last partial response
                        # self._sentence_text_packet['partial'] = False # TODO verify this
                        _process_sentence_text_packet()

                # NOTE: This must be true.. as if not partial, then it is a final complete response, which also is a start
                # This is here just to debug the logic of previous pipeline stage
                # So it should be removed at some point
                if not in_text_packet.start:
                    logger.error(f"in_text_packet.start should be True at this full response stage: {in_text_packet}")
                    raise Exception("start should be True at this full response stage")

                # a complete response is yielded at the end
                # NOTE: next partial_bot_res.get('start') is gonna be True
                self.log("", end='\n')

        if self._audiopacket_generator:
            try:
                out_audio_packet: AudioPacket = next(self._audiopacket_generator)
                out_audio_packet._id = self._generated_audio_packet_per_sentence_count
                self._generated_audio_packet_per_sentence_count += 1
                return out_audio_packet

            except StopIteration:
                self._audiopacket_generator = None

        if in_text_packet: # and no audio is being generated at the moment
            return True # Meaning that the dispatching is still ongoing

    def on_sleep(self):
        self.log('<tts>')

    def on_interrupt(self):
        super().on_interrupt()
        self._audiopacket_generator = None
        self._sentence_text_packet = None
        self._generated_audio_packet_per_sentence_count = 0


    def read(self, text: Union[TextPacket, str], as_generator=False) -> Generator[AudioPacket, None, None]:
        if not isinstance(text, TextPacket):
            if isinstance(text, str):
                text_packet = TextPacket(text, partial=False, start=False)
            else:
                raise Exception(f"Unsupported text type: {type(text)}")
                
        audio_bytes_generator = self.endpoint.text_to_audio(text_packet)
        if as_generator:
            return audio_bytes_generator
        else:
            audio_packet = reduce(lambda x, y: x + y, audio_bytes_generator)
            return audio_packet
        


    def _unpack(self) -> TextPacket:
        data_packets: List[TextPacket] = self._intermediate_input_buffer
        self._intermediate_input_buffer = []

        if not self._intermediate_input_buffer: # if intermediate buffer is empty, we need to get at least one packet from input buffer
            data_packet = self._input_buffer.get(timeout=None) # blocking call at least for the first time
            data_packets.append(data_packet)
        else:
            logger.debug("Intermediate buffer is not empty, skipping first get from input buffer")

        # Now we have at least one packet in data_packets, we can try to get more packets
        while True:
            try:
                data_packet = self._input_buffer.get_nowait()
                data_packets.append(data_packet)
            except QueueEmpty:
                # if len(data_packets) == 0:
                #     # logger.warning('No audio packets found in buffer', flush=True)
                #     return
                break

        complete_data_packet = data_packets[0]
        for i, data_packet in enumerate(data_packets[1:], start=1):
            try:
                complete_data_packet += data_packet
            except SequenceMismatchException as e:
                for j in range(i, len(data_packets)):
                    self._intermediate_input_buffer.append(data_packets[j])
                break
        
        return complete_data_packet

    def start(self, host):
        """Start processing thread"""
        logger.info(f'Starting {self}')

        self._host = host

        self.on_start()

        def _start_thread():
            while True:
                with self._lock:
                    logger.debug(f"Unpacking data in {self.__class__.__name__}")
                    data = self._unpack()
                    logger.debug(f"Unpacked data: {data}")
                    assert isinstance(data, TextPacket), f"Expected TextPacket, got {type(data)}"
                    data_packet = self._process(data)
                    logger.success(f"Processed data packet: {data_packet}")
                    
                    if self._is_interrupt_signal_pending:
                        logger.warning(f"Interrupt signal pending in {self.__class__.__name__}, calling on_interrupt")
                        self.on_interrupt()

                    logger.debug(f"Data packet after processing: {data_packet}")
                    if data_packet is not None and not isinstance(data_packet, bool):
                        # TODO this is just hacky way.. use proper standards
                        self.on_ready(data_packet)
                        logger.debug(f"Data packet {data_packet} sent to on_ready in {self.__class__.__name__}")
                    

        self._processor = self._host.start_background_task(_start_thread)
