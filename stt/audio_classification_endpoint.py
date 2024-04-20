from typing import Generator
from abc import ABC, abstractmethod
from transformers import pipeline
from storage_manager import write_output
from loguru import logger


class AudioClassificationEndpoint(ABC):
    @abstractmethod
    def detect(self, preprocessed_mic: Generator) -> Generator:
        raise NotImplementedError

    @property
    @abstractmethod
    def sample_rate(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def frame_size(self):
        raise NotImplementedError


class HFAudioClassificationEndpoint:
    def __init__(
        self,
        model_name: str = "MIT/ast-finetuned-speech-commands-v2",
        wake_word: str = "marvin",
        prediction_prob_threshold: float = 0.7,
        device: str = "cuda",
    ):
        self._classifier = pipeline(
            "audio-classification", model=model_name, device=device,
        )
        self.prediction_prob_threshold = prediction_prob_threshold

        if wake_word not in self._classifier.model.config.label2id.keys():
            raise ValueError(
                f"Wake word {wake_word} not in set of valid class labels,"
                f"pick a wake word in the set {self._classifier.model.config.label2id.keys()}."
            )

        self.wake_word = wake_word

        logger.info(
            f"Wakeword set is {self.wake_word} out of {self._classifier.model.config.label2id.keys()}"
        )

    def detect(self, preprocessed_mic: Generator) -> Generator:
        is_detected = False
        for prediction in self._classifier(preprocessed_mic):
            write_output("<", end="")
            prediction = prediction[0]
            if prediction["label"] == self.wake_word:
                if prediction["score"] > self.prediction_prob_threshold:
                    is_detected = True
                    break
        if is_detected:
            return True
        return False

    @property
    def sample_rate(self):
        return self._classifier.feature_extractor.sampling_rate

    @property
    def frame_size(self):
        return 320