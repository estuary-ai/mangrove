import sys
import os, argparse
from flask import Flask
from loguru import logger
from flask_socketio import SocketIO, Namespace
from assistant_controller import AssistantController
from storage_manager import StorageManager, write_output
from multiprocessing import Lock


class DigitalAssistant(Namespace):
    """Digital Assistant SocketIO Namespace"""

    def __init__(
        self,
        namespace="/",
        **assistant_kwargs,
    ):
        super().__init__(namespace)
        self.current_clients_ids = []
        self.namespace = namespace
        self.assistant_controller = AssistantController(**assistant_kwargs)
        self.lock = Lock()
        logger.info("Server is about to be Up and Running..")

    def setup(self):
        if self.server is None:
            raise RuntimeError("Server is not initialized yet")
        self.assistant_controller.start(self.server)
        self.responding_task = self.server.start_background_task(self.bg_responding_task)

    def __emit__(self, event, data):
        if hasattr(data, "__next__"):
            # if data is generator
            logger.debug(f"Emitting generator {event}")
            for d in data:
                write_output(">", end="")
                if hasattr(d, "to_dict"):
                    d = d.to_dict()
                self.server.emit(event, d)
        else:
            logger.debug(f"Emitting {event}")
            if hasattr(data, "to_dict"):
                data = data.to_dict()
            self.server.emit(event, data)

    def emit_bot_voice(self, data):
        logger.debug("emmiting bot_voice")
        self.__emit__("bot_voice", data)

    def emit_bot_response(self, data):
        logger.debug("emmiting bot_response")
        self.__emit__("bot_response", data)


    def on_connect(self):
        logger.info("client connected")
        StorageManager.establish_session()
        self.assistant_controller.on_connect(self)


    def on_disconnect(self):
        logger.info("client disconnected\n")
        with self.lock:
            self.assistant_controller.clean_up()
        StorageManager.clean_up()

    def on_stream_audio(self, audio_data):
        with self.lock:
            # Feeding in audio stream
            write_output("-", end="")
            self.assistant_controller.feed_audio_stream(audio_data)

    def on_trial(self, data):
        write_output(f"received trial: {data}")

    def bg_responding_task(self):
        # READ BUFFER AND EMIT AS NEEDED
        from queue import Empty
        while True:
            is_responding = False
            with self.lock:
                try:
                    bot_res, bot_voice_bytes = self.assistant_controller.receive()
                    if bot_voice_bytes is not None:
                        self.emit_bot_voice(bot_voice_bytes)
                    if bot_res is not None:
                        self.emit_bot_response(bot_res)
                    is_responding = True
                except Empty:
                    pass

            if not is_responding:
                # print('<waiting>', end='', flush=True)
                socketio.sleep(0.1)


    # def on_error(self, e):
    #     logger.error(f"Error: {e}")
    #     self.emit("error", {"msg": str(e)}, status=ClientStatus.NOT_CONNECTED)


if __name__ == "__main__":
    # TODO use a yml config file with internal configurations
    parser = argparse.ArgumentParser(description="Digital Assistant Endpoint")
    parser.add_argument(
        "--cpu", dest="cpu", default=False, action="store_true",
        help="Use CPU instead of GPU"
    )
    parser.add_argument(
        "--tts_endpoint", dest="tts_endpoint", type=str, default="pyttsx3",
        choices=["pyttsx3", "gtts", "elevenlabs", "tts"],
        help="TTS Endpoint"
    )
    parser.add_argument(
        "--port", dest="port", type=int, default=4000, help="Port number"
    )
    parser.add_argument(
        "--debug", dest="debug", type=bool, default=False, help="Debug mode"
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
        async_handlers=False
    )

    # @socketio.on_error_default  # handles all namespaces without an explicit error handler
    # def default_error_handler(e):
    #     write_output(f'Error debug {e}')
    #     # stt.reset_audio_stream()
    #     # # TODO reset anything

    device = "cuda" if not args.cpu else "cpu"
    digital_assistant = DigitalAssistant(
        namespace="/",
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
        f"\nYour Digital Assistant is running on port {args.port}. \n# Hints:"
        + '1. Run "ipconfig" in your terminal and use Wireless LAN adapter Wi-Fi IPv4 Address.\n'
        + "2. Ensure your client is connected to the same WIFI connection.\n"
        + "3. Ensure firewall shields are down in this particular network type with python.\n"
        + "4. Ensure your client microphone is not used by any other services such as windows speech-to-text api.\n"
        + "Fight On!"
    )
    logger.info(_msg)

    socketio.run(app, host="0.0.0.0", port=args.port, use_reloader=False)
