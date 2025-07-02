from typing import Optional, Dict
from abc import abstractmethod, ABCMeta

from flask import Flask
from flask_socketio import SocketIO, Namespace
from storage_manager import StorageManager, write_output
from multiprocessing import Lock
from core import AudioPacket, TextPacket, DataPacket
from core.stage import PipelineSequence
from core.utils import logger


# TODO create feedback loop (ACK), and use it for interruption!! 

class HostNamespace(Namespace, metaclass=ABCMeta):
    @abstractmethod
    def start_background_task(self, target, *args, **kwargs):
        """Start a background task in the server"""
        raise NotImplementedError("This method should be implemented in the subclass")
    

class SocketIONamespace(HostNamespace):
    """Digital Assistant SocketIO Namespace"""

    def __init__(
        self,
        agent: PipelineSequence,
        namespace="/",
    ):
        super().__init__(namespace)
        self.server: Optional[SocketIO]
        self.namespace = namespace
        self.agent = agent
        self.__lock__ = Lock()

    def setup(self) -> None:
        if self.server is None:
            raise RuntimeError("Server is not initialized yet")
        self.agent.start(self)

    def start_background_task(self, target, *args, **kwargs): # TODO find convenient generic type hinting
        if self.server is None:
            raise RuntimeError("Server is not initialized yet")
        return self.server.start_background_task(target, *args, **kwargs)

    def __emit__(self, event, data: DataPacket) -> None:
        assert isinstance(data, DataPacket), f"Expected DataPacket, got {type(data)}"
        logger.trace(f"Emitting {event}")
        if hasattr(data, "to_dict"):
            data = data.to_dict()
        self.server.emit(event, data)

    def emit_bot_voice(self, audio_packet: AudioPacket) -> None:
        self.__emit__("bot_voice", audio_packet)

    def emit_bot_response(self, text_packet: TextPacket) -> None:
        self.__emit__("bot_response", text_packet)

    def emit_stt_response(self, text_packet: TextPacket) -> None:
        self.__emit__("stt_response", text_packet)

    def emit_interrupt(self, timestamp: int) -> None:
        self.server.emit("interrupt", timestamp) 

    def on_connect(self):
        logger.info("client connected")
        StorageManager.establish_session()
        self.agent.on_connect()

    def on_disconnect(self):
        logger.info("client disconnected\n")
        with self.__lock__:
            self.agent.on_disconnect()
        StorageManager.clean_up()

    def on_stream_audio(self, audio_data: Dict):
        with self.__lock__:
            # Feeding in audio stream
            write_output("-", end="")
            from core import AudioPacket
            self.agent.feed(AudioPacket(data_json=audio_data))

    # def on_trial(self, data):
    #     write_output(f"received trial: {data}")

    # def on_error(self, e):
    #     logger.error(f"Error: {e}")
    #     self.emit("error", {"msg": str(e)}, status=ClientStatus.NOT_CONNECTED)


class FlaskSocketIOHost:
    """Flask SocketIO Host for the Digital Assistant"""

    def __init__(
        self, 
        agent: PipelineSequence, 
        namespace="/",
        flask_secret_key: str = "secret!",
        is_logging: bool = False,
    ):
        self.app = Flask(__name__)
        self.app.config["SECRET_KEY"] = flask_secret_key
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            cors_credentials=True,
            logger=is_logging,
            async_handlers=False
        )
        self.agent = agent
        self.host = SocketIONamespace(agent=agent, namespace=namespace)
        self.socketio.on_namespace(self.host)

    @property
    def namespace(self) -> str:
        """Get the namespace of the host"""
        return self.host.namespace

    def run(self, host="0.0.0.0", port=5000):
        logger.info("Starting the server...")
        self.socketio.on_namespace(self.host)
        self.host.setup()
        logger.info(f"Running server on {host}:{port} with namespace {self.namespace}")
        self.socketio.run(self.app, host=host, port=port, use_reloader=False)