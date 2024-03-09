import sys
import os, argparse
from flask import Flask
from loguru import logger
from flask_socketio import SocketIO, Namespace
from assistant_controller import AssistantController
from storage_manager import StorageManager, write_output
from multiprocessing import Lock
from memory import WorldState

class DigitalAssistant(Namespace):
    """Digital Assistant SocketIO Namespace"""

    def __init__(
        self,
        namespace="/",
        verbose=False,
        **assistant_kwargs,
    ):
        super().__init__(namespace)
        self.current_clients_ids = []
        self.namespace = namespace
        self.assistant_controller = AssistantController(**assistant_kwargs)
        self.lock = Lock()
        self.verbose = verbose  # TODO use it
        logger.info("Server is about to be Up and Running..")

    def setup(self):
        if self.server is None:
            raise RuntimeError("Server is not initialized yet")
        self.responding_task = self.server.start_background_task(self.bg_responding_task)

    def on_connect(self):
        logger.info("client connected")
        StorageManager.establish_session()
        bot_voice_bytes = self.assistant_controller.startup()
        if bot_voice_bytes:
            logger.info("emmiting bot_voice")
            self.server.emit("bot_voice", bot_voice_bytes)

    def on_disconnect(self):
        logger.info("client disconnected\n")
        with self.lock:
            self.assistant_controller.clean_up()
        StorageManager.clean_up()

    def on_stream_audio(self, audio_data):
        with self.lock:
            # Feeding in audio stream
            print("-", end="", flush=True)
            self.assistant_controller.feed_audio_stream(audio_data)

    def on_trial(self, data):
        write_output(f"received trial: {data}")

    def on_update_world_state(self, state):
        WorldState.update(state)

    def bg_responding_task(self):
        # READ BUFFER AND EMIT AS NEEDED
        while True:
            socketio.sleep(0.2)
            with self.lock:
                if self.assistant_controller.is_awake():
                    self.apply_communication_logic()
                    # TODO introduce timeout
                else:
                    wakeUpWordDetected = (
                        self.assistant_controller.is_wake_word_detected()
                    )
                    if wakeUpWordDetected:
                        self.server.emit("wake_up")

    def apply_communication_logic(self):
        stt_res = self.assistant_controller.process_audio_buffer()
        if stt_res is None:
            return

        # Now assisant is not awake
        logger.success(f"User: {stt_res}")
        self.server.emit("stt_response", stt_res)

        try:
            bot_res, bot_voice_bytes = self.assistant_controller.respond(stt_res["text"])
            assert not bot_res.get("partial")

            # TODO Include timestamps
            if bot_voice_bytes:
                logger.info("emmiting bot_voice")
                self.server.emit("bot_voice", bot_voice_bytes)

            logger.info("emitting bot_response")
            self.server.emit("bot_response", bot_res)
            logger.success(f"Bot: {bot_res}")

        except Exception as e:
            logger.error(f"Error: {e}")
            self.server.emit("bot_repsonse", {"msg": "bot is not available"})



if __name__ == "__main__":
    # TODO use a yml config file with internal configurations
    parser = argparse.ArgumentParser(description="Digital Assistant Endpoint")
    parser.add_argument(
        "--cpu", dest="cpu", default=False, action="store_true",
        help="Use CPU instead of GPU"
    )
    parser.add_argument(
        "--tts_endpoint", dest="tts_endpoint", type=str, default="pyttsx3",
        choices=["pyttsx3", "gtts", "elevenlabs"],
        help="TTS Endpoint"
    )
    parser.add_argument(
        "--port", dest="port", type=int, default=4000, help="Port number"
    )
    parser.add_argument(
        "--name",
        dest="name",
        type=str,
        default="Marvin",
        help="Digital Assistant Name (NOT CHANGEABLE YET)",
    )
    parser.add_argument(
        "--debug", dest="debug", type=bool, default=False, help="Debug mode"
    )
    parser.add_argument(
        "--verbose", dest="verbose", type=bool, default=False, help="Verbose mode"
    )
    parser.add_argument("--log", dest="log", type=bool, default=False, help="Log mode")
    parser.add_argument(
        "--flask_secret_key", dest="flask_secret_key", type=str, default="secret!",
        help="Flask secret key",
    )
    args = parser.parse_args()

    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1" # force CPU

    app = Flask(__name__)
    app.config["SECRET_KEY"] = args.flask_secret_key
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        cors_credentials=True,
        logger=args.log,
        engineio_logger=args.log,
    )

    # @socketio.on_error_default  # handles all namespaces without an explicit error handler
    # def default_error_handler(e):
    #     write_output(f'Error debug {e}')
    #     # stt.reset_audio_stream()
    #     # # TODO reset anything

    digital_assistant_name = args.name
    device = "cuda" if not args.cpu else "cpu"
    digital_assistant = DigitalAssistant(
        namespace="/",
        assistant_name=digital_assistant_name,
        verbose=args.verbose,
        tts_endpoint=args.tts_endpoint,
        device=device,
    )
    socketio.on_namespace(digital_assistant)
    digital_assistant.setup()



    # Show up to DEBUG logger level in console
    logger.remove()
    logger.add(sys.stdout, level="DEBUG", enqueue=True)

    # host_ip_address = socket.gethostbyname(socket.gethostname())
    _msg = (
        f"\nYour Digital Assistant {digital_assistant_name} running on port {args.port}. \n# Hints:"
        + '1. Run "ipconfig" in your terminal and use Wireless LAN adapter Wi-Fi IPv4 Address.\n'
        + "2. Ensure your client is connected to the same WIFI connection.\n"
        + "3. Ensure firewall shields are down in this particular network type with python.\n"
        + "4. Ensure your client microphone is not used by any other services such as windows speech-to-text api.\n"
        + "Fight On!"
    )
    logger.info(_msg)

    socketio.run(app, host="0.0.0.0", port=args.port, use_reloader=False)
