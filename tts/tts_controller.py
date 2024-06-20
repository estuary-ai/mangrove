from string import punctuation
from typing import Generator
from loguru import logger
from itertools import chain

from core.data import AudioPacket, TextPacket
from core.stage import TextToAudioStage
from .endpoints.base import TTSEndpoint


class TTSController(TextToAudioStage):
    """Text to speech controller"""

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
        if endpoint == "pyttsx3":
            logger.info("Using Pyttsx3 TTS Endpoint")
            from tts.endpoints.pyttsx3 import Pyttsx3TTSEndpoint
            self.endpoint = Pyttsx3TTSEndpoint(**endpoint_kwargs)
        elif endpoint == "tts":
            from tts.endpoints.xtts import TTSLibraryEndpoint
            self.endpoint = TTSLibraryEndpoint()
        elif endpoint == "elevenlabs":
            from tts.endpoints.elevenlabs import ElevenLabsTTSEndpoint
            logger.info("Using ElevenLabs TTS Endpoint")
            self.endpoint = ElevenLabsTTSEndpoint()
        elif endpoint == "gtts":
            from tts.endpoints.gtts import GTTSEndpoint
            logger.info("Using GTTS TTS Endpoint")
            self.endpoint = GTTSEndpoint()
        else:
            raise Exception(f"Unknown Endpoint {endpoint}, available endpoints: pyttsx3, tts")

        self._sentence_text_packet = None
        self._audiopacket_generator: Generator[AudioPacket, None, None] = None
        self._generated_audio_packet_per_sentence_count = False


    def _process(self, in_text_packet: TextPacket):
        # accepts a stream of text packets
        # upon completion of a sentence (detection component), a stream is yielded
        # sends a stream of audio packets

        def _process_sentence_text_packet():
            _new_audiopacket_generator = self._get_audiopackets_stream(
                self._sentence_text_packet.text
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

        if self._audiopacket_generator:
            try:
                out_audio_packet: AudioPacket = next(self._audiopacket_generator)
                out_audio_packet._id = self._generated_audio_packet_per_sentence_count
                self._generated_audio_packet_per_sentence_count += 1
                return out_audio_packet

            except StopIteration:
                self._audiopacket_generator = None

        if in_text_packet:
            if in_text_packet.partial:
                self.log(f"{in_text_packet.text}")

                if self._sentence_text_packet is None:
                    if in_text_packet.start:
                        self._generated_audio_packet_per_sentence_count = 0
                        self.log("SENVA: ")
                    # implement SentenceTextDataBuffer
                    self._sentence_text_packet: TextPacket = in_text_packet
                else:
                    self._sentence_text_packet += in_text_packet

                if self._sentence_text_packet.text.endswith(('?', '!', '.')):
                    # TODO prompt engineer '.' and check other options
                    _process_sentence_text_packet()

            else:
                # NOTE: _process leftover sentence_text_packet if any
                if self._sentence_text_packet is not None:
                    if len(self._sentence_text_packet.text.replace(punctuation, '').strip()) > 0:
                        assert not self._sentence_text_packet.partial, "Partial should be False" # NOTE: this is the last partial response
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

            return True # Meaning that the dispatching is still ongoing

    def on_sleep(self):
        self.log('<tts>')

    def _get_audiopackets_stream(self, text) -> Generator[AudioPacket, None, None]:
        """Get generated audio packets stream for text

        Args:
            text (str): Text to read

        Returns:
            Generator[AudioPacket, None, None]: Audio packets stream reading the text
        """
        if text is None:
            raise Exception("Texts cannot be None")

        if isinstance(text, list):
            text = " ".join(text)

        logger.debug(f"Reading text: {text}")
        yield from self.endpoint.text_to_bytes(text)

    def read(self, text, as_generator=False) -> Generator[AudioPacket, None, None]:
        if isinstance(text, str):
            audio_bytes_generator = self._get_audiopackets_stream(text)
        else:
            raise ValueError("text should be a string")

        if as_generator:
            return audio_bytes_generator
        else:
            from functools import reduce
            audio_packet = reduce(lambda x, y: x + y, audio_bytes_generator)
            return audio_packet