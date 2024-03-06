import os
import inflect
import backoff
from decimal import Decimal
from storage_manager import StorageManager, write_output
from tts.tts_endpoint import TTSEndpoint, Pyttsx3TTSEndpoint, TTSLibraryEndpoint, ElevenLabsTTSEndpoint

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
            self.endpoint = Pyttsx3TTSEndpoint(**endpoint_kwargs)
        elif endpoint == "tts":
            self.endpoint = TTSLibraryEndpoint()
        elif endpoint == "elevenlabs":
            self.endpoint = ElevenLabsTTSEndpoint()
        else:
            raise Exception(f"Unknown Endpoint {endpoint}, available endpoints: pyttsx3, tts")

        self.storage_manager = StorageManager()
        self.number_to_word_converter = inflect.engine()
        self.created_audio_files = []


    def _create_audio_files(self, texts):
        """Create audio files from texts and return list of filepaths

        Args:
            texts (list): List of texts to convert to audio files
        Returns:
            list: List of filepaths of created audio files
        """
        recent_created_audio_files = []
        for text in texts:
            filepath = self.storage_manager.get_generated_audio_path(text)
            self.endpoint.text_to_audio_file(text, filepath)
            recent_created_audio_files.append(filepath)

        self.created_audio_files += recent_created_audio_files
        return recent_created_audio_files

    def _get_audio_bytes_stream(self, texts):
        """Get audio bytes stream from texts

        Args:
            texts (list or str): Texts to convert to audio bytes stream
        Returns:
            bytes: Audio bytes stream
        """
        if texts is None:
            raise Exception("Texts cannot be None")

        if not isinstance(texts, list):
            texts = [texts]

        # breakpoint()
        audio_files_bytes = b""
        for audio_file in self._create_audio_files(texts):
            @backoff.on_exception(backoff.expo, FileNotFoundError, max_tries=5)
            def get_audio_bytes(audio_file):
                return open(audio_file, "rb").read()
            audio_files_bytes += get_audio_bytes(audio_file)

        return audio_files_bytes

    def delete_audio_files(self):
        """Delete audio files created by this instance"""
        # TODO use and offload work to storage_manager
        for audio_file in self.created_audio_files:
            os.remove(audio_file)
        self.created_audio_files = []

    def get_feature_read_bytes(self, feature, values, units=None):
        """Get audio bytes stream for feature read

        Args:
            feature (str): Feature to read
            values (list): List of values to read
            units (list): List of units of values
        Returns:
            bytes: Audio bytes stream reading the feature with its value and ending with unit
        """
        text = feature.replace("_", " ") + " is equal to "
        if not units:
            units = ["" for _ in values]

        for value, unit in zip(values, units):
            write_output(value)
            text += self._textify_number(round(Decimal(value), 2)) + " " + unit
        write_output(text)
        return self._get_audio_bytes_stream(text)

    def get_plain_text_read_bytes(self, text):
        """Get audio bytes stream for plain text

        Args:
            text (str): Text to read
        Returns:
            bytes: Audio bytes stream reading the text
        """
        return self._get_audio_bytes_stream(text)

    def _textify_number(self, num):
        """Convert number to text
        Args:
            num (int or float): Number to convert
        Returns:
            str: Textified number
        """
        return self.number_to_word_converter.number_to_words(num)
