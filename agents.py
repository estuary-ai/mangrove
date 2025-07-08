import warnings
from typing import Dict, Callable, Union, TYPE_CHECKING
from abc import ABCMeta, abstractmethod

from core.data import data_packet
from mangrove import (
    VADStage,
    STTStage,
    BotStage,
    TTSStage,
)
from storage_manager import StorageManager
from core import AudioBuffer, DataPacket, AudioPacket, TextPacket
from core.stage import PipelineSequence, PipelineStage
from core.utils import logger

if TYPE_CHECKING:
    from host import SocketIONamespace

# TODO check on this later
warnings.filterwarnings("ignore", category=UserWarning)


class TextBasedAgentPipeline(PipelineSequence):
    """Pipeline for text-based agent processing."""
    input_type = TextPacket
    output_type = TextPacket

class VoiceCapableAgentPipeline(PipelineSequence):
    """Pipeline for voice-capable agent processing."""
    input_type = AudioPacket
    output_type = AudioPacket

    def on_start(self):
        super().on_start()
        self.session_audio_buffer = AudioBuffer()

    def on_connect(self):
        logger.info("Connected to the server.")
        if self.startup_audiopacket:
            from copy import deepcopy
            self._host.emit_bot_voice(deepcopy(self.startup_audiopacket))
        logger.info("Ready to receive audio packets.")

    def on_disconnect(self):
        """Clean up upon disconnection"""
        logger.info("Disconnected from the server.")
        if self.session_audio_buffer.is_empty():
            return
        StorageManager.write_audio_file(self.session_audio_buffer.dump_to_packet())
        StorageManager.ensure_completion()
        logger.info("Session completed.")


class Agent(metaclass=ABCMeta):
    """Base class for all agents."""
    def __init__(self):
        """Base class for all agents."""
        self.name = self.__class__.__name__

    def on_start(self):
        """Called when the agent is started."""
        logger.info(f"{self.name} agent started.")

    def on_connect(self):
        """Called when the agent connects to the server."""
        logger.info(f"{self.name} agent connected.")

    def on_disconnect(self):
        """Called when the agent disconnects from the server."""
        logger.info(f"{self.name} agent disconnected.")

    @abstractmethod
    def feed(self, data_packet: DataPacket):
        """Feed a data packet to the agent."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    def start(self, host):
        """Start the agent with the given host."""
        raise NotImplementedError("This method should be implemented by subclasses.")

class BasicConversationalAgent(Agent):
    """Agent controller for the conversational AI server."""

    def __init__(
        self,
        text_only: bool = False,
        device=None,
        endpoints: Dict[str, str] = {
            "bot": "openai",
            "tts": "gtts",
        },
        persona_configs: Union[str, Dict] = None,
        welcome_msg: str="Welcome, AI server connection is succesful.",
        verbose=False,
    ):
        super().__init__()

        vad = VADStage(name="vad", device=device)
        stt = STTStage(name="stt", device=device)
        bot = BotStage(name="bot", endpoint=endpoints["bot"], persona_configs=persona_configs, verbose=verbose)
        tts = TTSStage(name="tts", endpoint=endpoints["tts"])

        self.startup_audiopacket = None
        # if welcome_msg:
        #     self.startup_audiopacket = tts.read(
        #         welcome_msg,
        #         as_generator=False
        #     )

        if text_only:
            self._pipeline: TextBasedAgentPipeline = TextBasedAgentPipeline(
                name="text_based_agent_pipeline",
                stages=[
                    bot,
                ],
                verbose=verbose,
            )
            
        else:
            self._pipeline: VoiceCapableAgentPipeline = VoiceCapableAgentPipeline(
                name="voice_capable_agent_pipeline",
                stages=[
                    vad,
                    stt,
                    bot,
                    tts
                ],
                verbose=verbose,
            )
        self._text_only = text_only

    def start(self, host: "SocketIONamespace"):
        """Start the agent with the given host."""
        self.host = host
        self._pipeline.response_emission_mapping = {
            "stt": self.host.emit_stt_response,
            "bot": self.host.emit_bot_response,
            "tts": self.host.emit_bot_voice,
        }
        self._pipeline.start(host=self.host)

    def feed(self, data_packet: DataPacket):
        """Feed a data packet to the appropriate agent pipeline."""
        if not isinstance(data_packet, self._pipeline.input_type):
            raise ValueError(f"Cannot feed data packet of type {type(data_packet)} to the agent pipeline {self._pipeline.name}. Expected type {self._pipeline.input_type}.")
        self._pipeline.feed(data_packet)
       