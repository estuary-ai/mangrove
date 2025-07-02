from string import punctuation
from typing import Iterator, Union
from functools import reduce

from core.utils import logger
from core.data import AudioPacket, TextPacket, DataPacketStream
from core.stage import TextToAudioStage
from core.context import IncomingPacketWhileProcessingException
from .endpoints.base import TTSEndpoint


class TTSStage(TextToAudioStage):
    """Text to speech Stage"""

    input_type = TextPacket
    output_type = AudioPacket

    def __init__(
        self,
        name: str,
        endpoint="pyttsx3",
        endpoint_kwargs={
            "voice_rate": 140,
            "voice_id": 10,
        },
        verbose=False,
    ):
        super().__init__(name=name, verbose=verbose)
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
        self.debug = False

    def process(self, in_text_packet: TextPacket) -> None:
        """Process the incoming TextPacket and convert it to AudioPacket(s)
        Args:
            in_text_packet (TextPacket): The incoming text packet to process.
        """ 
        assert isinstance(in_text_packet, TextPacket), f"Expected TextPacket, got {type(in_text_packet)}"
        logger.success(f"Processing: {in_text_packet}")

        if in_text_packet.partial:
            if in_text_packet.start:
                # if this is the start of a new sentence, reset the sentence_text_packet
                if self._sentence_text_packet is not None:
                    logger.error(f"Unexpected start in partial response: {in_text_packet}, resetting sentence_text_packet")
                    self._sentence_text_packet = None
                    self.log("SENVA: ")
                    
            self.log(f"{in_text_packet.text}")

            if self._sentence_text_packet is None:
                if in_text_packet.start:
                    self.log("SENVA: ")
                # TODO implement SentenceTextDataBuffer
                self._sentence_text_packet: TextPacket = in_text_packet

            else:
                if in_text_packet.start:
                    self._sentence_text_packet = in_text_packet
                    # self.schedule_forward_interrupt()
                    # TODO investigate this
                    logger.error(f"Partial response should not have start: {in_text_packet}, interrupting and starting new")
                else:
                    self._sentence_text_packet += in_text_packet

            # TODO uncomment this back
            # if self._sentence_text_packet.text.endswith(('?', '!', '.')):
            #     # TODO prompt engineer '.' and check other options
            #     _new_audiopacket_generator = self.read(
            #         self._sentence_text_packet,
            #         as_generator=True
            #     )
            #     logger.debug(f"Packing audiopacket generator corresponding to sentence: {self._sentence_text_packet.text}")
            #     self._sentence_text_packet = None  # NOTE: reset complete_segment because you got a complete response
            #     self.pack(_new_audiopacket_generator)

        else:
            # NOTE: _process leftover sentence_text_packet if any
            if self._sentence_text_packet is not None:
                if len(self._sentence_text_packet.text.replace(punctuation, '').strip()) > 0:
                    # assert not self._sentence_text_packet.partial, "Partial should be False" # NOTE: this is the last partial response
                    # self._sentence_text_packet['partial'] = False # TODO verify this
                    _new_audiopacket_generator = self.read(
                        self._sentence_text_packet,
                        as_generator=True
                    )
                    logger.debug(f"Packing audiopacket generator corresponding to sentence: {self._sentence_text_packet.text}")
                    self._sentence_text_packet = None  # NOTE: reset complete_segment because you got a complete response
                    self.pack(_new_audiopacket_generator)

            # NOTE: This must be true.. as if not partial, then it is a final complete response, which also is a start
            # This is here just to debug the logic of previous pipeline stage
            # So it should be removed at some point
            if not in_text_packet.start:
                logger.error(f"in_text_packet.start should be True at this full response stage: {in_text_packet}")
                raise Exception("start should be True at this full response stage")

            # a complete response is yielded at the end
            # NOTE: next partial_bot_res.get('start') is gonna be True
            self.log("", end='\n')

    # def on_interrupt(self):
    #     super().on_interrupt()
    #     self._sentence_text_packet = None

    def read(self, text: Union[TextPacket, str], as_generator=False) -> Generator[AudioPacket, None, None]:
        if not isinstance(text, TextPacket):
            if isinstance(text, str):
                text = TextPacket(text, partial=False, start=False)
            else:
                raise Exception(f"Unsupported text type: {type(text)}")

        audio_bytes_generator: Generator[AudioPacket, None, None] = self.endpoint.text_to_audio(text)
        if as_generator:
            def _generator_with_identification() -> Generator[AudioPacket, None, None]:
                """Generator that yields AudioPacket objects from the audio bytes generator."""
                for idx, audio_packet in enumerate(audio_bytes_generator):
                    audio_packet._id = idx
                    yield audio_packet
            return _generator_with_identification()
        else:
            audio_packet = reduce(lambda x, y: x + y, audio_bytes_generator)
            return audio_packet
        
    def on_incoming_packet_while_processing(self, e: IncomingPacketWhileProcessingException, data: DataPacketStream) -> None:
        # TODO maybe we should consider taking values that have been propagated although not yet processed by next stage
        logger.warning(f"Invalidating stream due to: {e}, hence stopping this stream: {data}")      
        # TODO if some chunk has been been processed by this, as well as by next stage, we should take the part that has been,
        # TODO then we should append it to the history, and reset the in-progress user text packet!
        # TODO note tho that the incoming packet, could have been before then concatenated with the in-progress user text packet
        return True # stop current response generation