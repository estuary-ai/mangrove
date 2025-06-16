from string import punctuation
from typing import Generator, Union, List
from itertools import chain
from functools import reduce

from core.utils import logger
from core.data import AudioPacket, TextPacket
from core.stage import TextToAudioStage
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
        self.debug = False

    def process(self, in_text_packet: TextPacket) -> None:
        """Process the incoming TextPacket and convert it to AudioPacket(s)
        Args:
            in_text_packet (TextPacket): The incoming text packet to process.
        """ 
        assert isinstance(in_text_packet, TextPacket), f"Expected TextPacket, got {type(in_text_packet)}"

        logger.success(f"Processing: {in_text_packet}")
        if in_text_packet.partial:
            self.log(f"{in_text_packet.text}")

            if self._sentence_text_packet is None:
                if in_text_packet.start:
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
                _new_audiopacket_generator = self.read(
                    self._sentence_text_packet,
                    as_generator=True
                )
                logger.debug(f"Packing audiopacket generator corresponding to sentence: {self._sentence_text_packet.text}")
                self.pack(_new_audiopacket_generator)
                # NOTE: reset complete_segment because you got a complete response
                self._sentence_text_packet = None

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
                    self.pack(_new_audiopacket_generator)
                    # NOTE: reset complete_segment because you got a complete response
                    self._sentence_text_packet = None

            # NOTE: This must be true.. as if not partial, then it is a final complete response, which also is a start
            # This is here just to debug the logic of previous pipeline stage
            # So it should be removed at some point
            if not in_text_packet.start:
                logger.error(f"in_text_packet.start should be True at this full response stage: {in_text_packet}")
                raise Exception("start should be True at this full response stage")

            # a complete response is yielded at the end
            # NOTE: next partial_bot_res.get('start') is gonna be True
            self.log("", end='\n')

    def on_interrupt(self):
        super().on_interrupt()
        self._sentence_text_packet = None

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