import sys
import argparse
import socketio
from misc import setup_terminate_signal_if_win
from sound_manager import SoundManager
from loguru import logger


class AssistantClient(socketio.ClientNamespace):
    """Assistant Client class. Handles the communication with the server."""

    def __init__(self, namespace):
        """Constructor

        Args:
            namespace (str): namespace to connect to
        """
        super().__init__(namespace)
        self.sound_manager = SoundManager(self._emit_audio_packet)
        self.is_connected = False

    def _emit_audio_packet(self, audio_packet):
        """Emits an audio packet to the server

        Args:
            audio_packet (bytes): audio packet to be sent to the server
        """
        if self.is_connected:
            print(".", end="", flush=True)
            self.emit("stream_audio", audio_packet)

    def on_connect(self):
        sio.emit("trial", "test")
        self.is_connected = True
        self.sound_manager.open_mic()
        logger.success("I'm connected!")

    def on_disconnect(self):
        logger.success("I'm disconnected!")
        self.is_connected = False
        self.sound_manager.close_mic()

    def on_connect_error(self, data):
        logger.warning(f"The connection failed!: {data}")

    # def on_wake_up(self):
    #     logger.info("Wake Up!")
    #     self.sound_manager.play_activation_sound()

    # def on_stt_response(self, data):
    #     """Handles the command transcription detected from the server

    #     Args:
    #         data (dict): command transcription received from the server
    #     """
    #     self.sound_manager.play_termination_sound()
    #     logger.debug(f"Stt response: {data}")

    def on_interrupt(self, timestamp: int):
        """Handles the interrupt signal received from the server"""
        logger.warning("Interrupt signal received!")
        self.sound_manager.interrupt(timestamp)

    def on_bot_voice(self, partial_audio_dict):
        """Handles the bot voice received from the server

        Args:
            partial_audio_dict (dict): bot voice received from the server
        """
        logger.debug(f"Playing bot_voice {partial_audio_dict['timestamp']}")
        self.sound_manager.play_audio_packet(partial_audio_dict)

    def on_bot_response(self, data):
        """Handles the bot response received from the server

        Args:
            data (dict): bot response received from the server
        """
        # Handle response here
        if not data['partial']:
            logger.debug(f"Bot: {data}")


def close_callback():
    """Callback to be called when the application is about to be closed"""
    sio.disconnect()
    sio.wait()
    logger.info("Bye Bye!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug", action="store_true", default=False, help="debug mode"
    )
    parser.add_argument(
        "--namespace", type=str, default="/", help="namespace to connect to"
    )
    parser.add_argument(
        "--address", type=str, default="localhost", help="server address to connect to"
    )
    parser.add_argument(
        "--port", type=int, default=4000, help="server port to connect to"
    )
    parser.add_argument("--timeout", type=int, default=10, help="connection timeout")
    parser.add_argument("--verbose", action="store_true", help="verbose mode")
    args = parser.parse_args()

    logger.add(sys.stderr, level="DEBUG")

    sio = socketio.Client(logger=args.debug, engineio_logger=args.debug)
    sio.register_namespace(AssistantClient(args.namespace))
    sio.connect(f"ws://{args.address}:{args.port}", wait_timeout=args.timeout)
    setup_terminate_signal_if_win(close_callback)
    sio.wait()
