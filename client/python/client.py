import argparse
import logging
import socketio
from misc import setup_terminate_signal_if_win
from sound_manager import SoundManager


class AssistantClient(socketio.ClientNamespace):
    """ Assistant Client class. Handles the communication with the server."""
    def __init__(self, namespace):
        """ Constructor
        
        Args:
            namespace (str): namespace to connect to
        """
        super().__init__(namespace) 
        self.sound_manager = SoundManager(self._emit_audio_packet)
        self.is_connected = False
    
    def _emit_audio_packet(self, audio_packet):
        """ Emits an audio packet to the server
        
        Args:
            audio_packet (bytes): audio packet to be sent to the server
        """
        if self.is_connected:
            self.emit("stream_audio", audio_packet)

    def on_connect(self):
        sio.emit('trial', "test")
        self.is_connected = True
        self.sound_manager.open_mic()
        logging.info("I'm connected!")

    def on_disconnect(self):
        logging.info("I'm disconnected!")
        self.is_connected = False
        self.sound_manager.close_mic()

    def on_connect_error(self, data):
        logging.warn(f"The connection failed!: {data}")

    def on_wake_up(self):
        logging.info('Wake Up!')
        # self.sound_manager.play_activation_sound()
        
    def on_stt_response(self, data):
        """ Handles the command transcription detected from the server
        
        Args:
            data (dict): command transcription received from the server
        """
        # self.sound_manager.play_termination_sound()
        logging.debug(f'Stt response: {data}')
        
    def on_bot_voice(self, audio_bytes):
        """ Handles the bot voice received from the server
        
        Args:
            audio_bytes (bytes): bot voice audio bytes received from the server
        """
        logging.debug(f'Playing bot_voice')
        self.sound_manager.play_audio_packet(audio_bytes)
        
    def on_bot_response(self, data):
        """ Handles the bot response received from the server
        
        Args:
            data (dict): bot response received from the server    
        """
        # Handle response here
        logging.debug(f'SENVA: {data}')
        
    def catch_all(self, event,  data):
        """ Handles all events not handled by the defined handlers"""
        logging.warn(f'receiving non handled event: {event}:: {data}')

def close_callback():
    """ Callback to be called when the application is about to be closed"""
    sio.disconnect()
    sio.wait()
    logging.info('Bye Bye!')
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', default=False, help='debug mode')
    parser.add_argument('--namespace', type=str, default='/', help='namespace to connect to')
    parser.add_argument('--address', type=str, default='localhost', help='server address to connect to')
    parser.add_argument('--port', type=int, default=4000, help='server port to connect to')
    parser.add_argument('--timeout', type=int, default=10, help='connection timeout')
    parser.add_argument('--verbose', action='store_true', help='verbose mode')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.DEBUG)

    
    sio = socketio.Client(logger=args.debug, engineio_logger=args.debug)
    sio.register_namespace(AssistantClient(args.namespace))
    sio.connect(
        f'ws://{args.address}:{args.port}',
        wait_timeout = args.timeout
    )
    setup_terminate_signal_if_win(close_callback)
    sio.wait()
    
    