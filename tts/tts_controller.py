import inflect
from typing import Generator, Dict
from storage_manager import StorageManager, write_output
from loguru import logger
from tts.endpoints.base import TTSEndpoint

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
