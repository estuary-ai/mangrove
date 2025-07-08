import sys
import argparse
import socketio
from misc import setup_terminate_signal_if_win
from sound_manager import SoundManager
from loguru import logger


class AssistantClient(socketio.ClientNamespace):
    """Assistant Client class. Handles the communication with the server."""

    def __init__(self, namespace, text_based: bool = False):
        """Constructor

        Args:
            namespace (str): namespace to connect to
        """
        super().__init__(namespace)
        self.text_based = text_based
        if not self.text_based:
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
        if not self.text_based:
            self.sound_manager.open_mic()
        logger.success("I'm connected!")

    def on_disconnect(self):
        logger.success("I'm disconnected!")
        self.is_connected = False
        if not self.text_based:
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
        if not self.text_based:
            # Interrupt the audio playback
            self.sound_manager.interrupt(timestamp)

    def on_bot_voice(self, partial_audio_dict):
        """Handles the bot voice received from the server

        Args:
            partial_audio_dict (dict): bot voice received from the server
        """
        if not self.text_based:
            self.sound_manager.play_audio_packet(partial_audio_dict)

    def on_bot_response(self, data):
        """Handles the bot response received from the server

        Args:
            data (dict): bot response received from the server
        """
        # Handle response here
        if data['partial']:
            if data['start']:
                self.print("=" * 20)
                self.print("AI:", end=" ")
            self.print(data['text'], end="")
        else:
            self.print()

    def on_stt_response(self, data):
        """Handles the STT response received from the server

        Args:
            data (dict): STT response received from the server
        """
        # Handle response here
        if data['start']:
            self.print("You:", end=" ")
        self.print(data['text'], end="")

    def print(self, *args, **kwargs):
        """Prints the message to the console"""
        print(*args, **kwargs, flush=True)

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
    parser.add_argument(
        "--text", action="store_true", default=False, help="text-based client mode"
    )
    parser.add_argument("--timeout", type=int, default=10, help="connection timeout")
    parser.add_argument("--verbose", action="store_true", help="verbose mode")
    args = parser.parse_args()

    logger.add(sys.stderr, level="DEBUG")

    sio = socketio.Client(logger=args.debug, engineio_logger=args.debug)
    sio.register_namespace(AssistantClient(args.namespace, text_based=args.text))
    sio.connect(f"ws://{args.address}:{args.port}", wait_timeout=args.timeout)
    setup_terminate_signal_if_win(close_callback)

    if args.text:
        print("Text-based client mode enabled. Type your messages below:")
        while True:
            try:
                message = input("You: ")
                if message.lower() in ["exit", "quit"]:
                    break
                sio.emit("text", {"text": message, "start": True, "partial": False})
            except KeyboardInterrupt:
                break
    else:
        print("Voice-based client mode enabled. Speak to the microphone.")
        sio.wait()
