import inflect
from typing import Generator, Dict
from storage_manager import StorageManager, write_output
from loguru import logger
from multiprocessing import JoinableQueue
from queue import Empty
from tts.endpoints.base import TTSEndpoint
from itertools import chain

class TTSController:
    """Text to speech controller"""

    def __init__(
        self,
        endpoint="pyttsx3",
        endpoint_kwargs={
            "voice_rate": 140,
            "voice_id": 10,
        }
    ):
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

        self.storage_manager = StorageManager()
        self.number_to_word_converter = inflect.engine()
        self.created_audio_files = []

        self._input_queue = JoinableQueue()
        self._output_buffer = JoinableQueue()

    def start(self, server):
        """Start TTS Controller Thread"""
        def _start_thread():
            voice_bytes_generator = None
            while True:
                try:
                    partial_bot_res = self._input_queue.get_nowait()
                except Empty:
                    partial_bot_res = None

                if partial_bot_res is None and voice_bytes_generator is None:
                    server.sleep(0.1)
                    # print('<tts>', end='', flush=True)
                    continue

                if voice_bytes_generator:
                    try:
                        partial_voice_bytes = next(voice_bytes_generator)
                        self._output_buffer.put((None, partial_voice_bytes))
                    except StopIteration:
                        voice_bytes_generator = None

                if partial_bot_res:
                    if partial_bot_res["start"]:
                        complete_segment = {'text': '', 'commands': []}
                        write_output("SENVA: ", end='')
                    else:
                        logger.debug(
                            f"Partial Bot Response: {partial_bot_res}"
                        )

                    if partial_bot_res["partial"]:
                        bot_text = partial_bot_res.get("text")
                        write_output(f"{bot_text}", end='')

                        try:
                            assert complete_segment is not None, "complete_segment should not be None"
                        except Exception:
                            logger.error("complete_segment is None")
                            breakpoint()

                        complete_segment['commands'] += partial_bot_res['commands']
                        complete_segment['text'] += partial_bot_res['text']
                        if complete_segment['text'].endswith(('?', '!', '.')):
                            # TODO prompt engineer '.' and check other options
                            complete_segment['partial'] = True
                            _new_voice_bytes_generator = self.get_plain_text_read_bytes(complete_segment['text'])
                            if voice_bytes_generator is not None:
                                voice_bytes_generator = chain(
                                    voice_bytes_generator,
                                    _new_voice_bytes_generator
                                )
                            else:
                                voice_bytes_generator = _new_voice_bytes_generator

                            # NOTE: reset complete_segment
                            complete_segment = {'text': '', 'commands': []}
                    else:
                        if len(complete_segment['text']):
                            # NOTE: this is the last partial response
                            complete_segment['partial'] = False
                            _new_voice_bytes_generator = self.get_plain_text_read_bytes(complete_segment['text'])
                            if voice_bytes_generator is not None:
                                voice_bytes_generator = chain(
                                    voice_bytes_generator,
                                    _new_voice_bytes_generator
                                )
                            else:
                                voice_bytes_generator = _new_voice_bytes_generator

                            # NOTE: reset complete_segment
                            complete_segment = {'text': '', 'commands': []}

                            # if not partial, then it is a final complete response
                            assert partial_bot_res['start'] is False, "start should be False at this full response stage"
                            # a complete response is yielded at the end
                            # NOTE: next partial_bot_res.get('start') is gonna be True
                            write_output("", end='\n')
                            self._output_buffer.put(
                                (partial_bot_res, None)
                            )

        self._process = server.start_background_task(_start_thread)

    def feed(self, text):
        """Feed text to TTS Controller"""
        self._input_queue.put(text)

    def receive(self):
        """Receive TTS Controller response"""
        try:
            return self._output_buffer.get_nowait()
        except Empty:
            return None

    def _get_audio_bytes_stream(self, text) -> Generator[Dict, None, None]:
        """Get audio bytes stream from texts

        Args:
            text (list or str): Texts to convert to audio bytes stream
        Returns:
            bytes: Audio bytes stream
        """
        if text is None:
            raise Exception("Texts cannot be None")

        if isinstance(text, list):
            text = " ".join(text)

        audio_packets_dicts_generator = self.endpoint.text_to_bytes(text)
        for audio_packet_dict in audio_packets_dicts_generator:
            yield {
                'audio_bytes': audio_packet_dict['audio_bytes'],
                'frame_rate': audio_packet_dict['frame_rate'],
                'sample_width': audio_packet_dict['sample_width'],
                'channels': audio_packet_dict['channels'],
            }

    def get_plain_text_read_bytes(self, text) -> Generator[Dict, None, None]:
        """Get audio bytes stream for plain text

        Args:
            text (str): Text to read
        Returns:
            bytes: Audio bytes stream reading the text
        """
        return self._get_audio_bytes_stream(text)




    # def _create_audio_files(self, texts):
    #     """Create audio files from texts and return list of filepaths

    #     Args:
    #         texts (list): List of texts to convert to audio files
    #     Returns:
    #         list: List of filepaths of created audio files
    #     """
    #     recent_created_audio_files = []
    #     for text in texts:
    #         filepath = self.storage_manager.get_generated_audio_path(text)
    #         self.endpoint.text_to_audio_file(text, filepath)
    #         recent_created_audio_files.append(filepath)

    #     self.created_audio_files += recent_created_audio_files
    #     return recent_created_audio_files


    # def delete_audio_files(self):
    #     """Delete audio files created by this instance"""
    #     # TODO use and offload work to storage_manager
    #     for audio_file in self.created_audio_files:
    #         os.remove(audio_file)
    #     self.created_audio_files = []


    # def get_feature_read_bytes(self, feature, values, units=None):
    #     """Get audio bytes stream for feature read

    #     Args:
    #         feature (str): Feature to read
    #         values (list): List of values to read
    #         units (list): List of units of values
    #     Returns:
    #         bytes: Audio bytes stream reading the feature with its value and ending with unit
    #     """
    #     text = feature.replace("_", " ") + " is equal to "
    #     if not units:
    #         units = ["" for _ in values]

    #     for value, unit in zip(values, units):
    #         write_output(value)
    #         text += self._textify_number(round(Decimal(value), 2)) + " " + unit
    #     write_output(text)
    #     return self._get_audio_bytes_stream(text)

    # def _textify_number(self, num):
    #     """Convert number to text
    #     Args:
    #         num (int or float): Number to convert
    #     Returns:
    #         str: Textified number
    #     """
    #     return self.number_to_word_converter.number_to_words(num)
