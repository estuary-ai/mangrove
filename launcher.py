import sys
import os, argparse
import torch
from dotenv import load_dotenv

from core.utils import logger
from host import FlaskSocketIOHost
from agents import BasicConversationalAgent

load_dotenv(override=True)

if __name__ == "__main__":
    # TODO use a yml config file with internal configurations
    parser = argparse.ArgumentParser(description="Run the Digital Companion Mangrove as a SocketIO server.")
    parser.add_argument(
        "--cpu", dest="cpu", default=False, action="store_true",
        help="Use CPU instead of GPU"
    )
    parser.add_argument(
        "--bot_endpoint", dest="bot_endpoint", type=str, default="openai",
        choices=["openai", "ollama"],
        help="Bot Conversational Endpoint"
    )
    parser.add_argument(
        "--tts_endpoint", dest="tts_endpoint", type=str, default="xtts",
        choices=["pyttsx3", "gtts", "elevenlabs", "xtts"],
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
        "--flask-secret-key", dest="flask_secret_key", type=str, default="secret!",
        help="Flask secret key"
    )
    parser.add_argument(
        "--persona", dest="persona", type=str, default=None,
        help="File path to persona json file"
    )
    parser.add_argument(
        "--namespace", dest="namespace", type=str, default="/",
        help="SocketIO namespace"
    )
    parser.add_argument(
        "--text-only", dest="text_only", action="store_true", default=False,
        help="Run in text-only mode (no audio processing)"
    )
    args = parser.parse_args()

    # Show up to DEBUG logger level in console
    logger.remove()
    logger.add(sys.stdout, level="DEBUG", enqueue=True)

    
    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1" # force CPU

    # @socketio.on_error_default  # handles all namespaces without an explicit error handler
    # def default_error_handler(e):
    #     write_output(f'Error debug {e}')
    #     # stt.reset_audio_stream()
    #     # # TODO reset anything

    if args.cpu:
        device = "cpu"
    elif torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    host = FlaskSocketIOHost()

    # Set default persona configs if none provided
    persona_configs = args.persona
    if persona_configs is None:
        if args.bot_endpoint == "openai":
            # Default persona config for OpenAI endpoint
            persona_configs = {"assistant_name": "Marvin"}
        elif args.bot_endpoint == "ollama":
            # Default persona config for Ollama endpoint - use a default persona file
            persona_configs = "mangrove/bot/persona/default_persona.json"

    # Configure endpoints based on text-only mode
    if args.text_only:
        # Text-only mode: only need bot endpoint
        endpoints = {"bot": args.bot_endpoint}
    else:
        # Voice mode: need both bot and TTS endpoints
        endpoints = {
            "bot": args.bot_endpoint,
            "tts": args.tts_endpoint
        }

    agent = BasicConversationalAgent(
        text_only=args.text_only,
        endpoints=endpoints,
        persona_configs=persona_configs,
        device=device,
        verbose=args.debug,
    )

    logger.success(
        f"\nYour Digital Assistant is running on port {args.port}."
        "\n# Hints:"
        + '1. Run "ipconfig" in your terminal and use Wireless LAN adapter Wi-Fi IPv4 Address.\n'
        + "2. Ensure your client is connected to the same WIFI connection.\n"
        + "3. Ensure firewall shields are down in this particular network type with python.\n"
        + "4. Ensure your client microphone is not used by any other services such as windows speech-to-text api.\n"
        + "Fight On!"
    )

    host.run(
        agent=agent,
        namespace=args.namespace,
        host="0.0.0.0",
        port=args.port
    )
