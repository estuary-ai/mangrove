import asyncio
import sys

from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig

class BotController:

    def __init__(self,
                 model_path='models/rasa-model/20220522-124602.tar.gz',
                 endpoint_config_address='http://localhost:5055/webhook'):
        
        self.agent =\
            Agent.load(
                model_path,
                action_endpoint=EndpointConfig(endpoint_config_address))

        if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def send_user_message(self, request):

        # user_message = request.get('Body')
        # conversation_id = request.get('From')
        conversation_id = 1
        user_message = request

        #Sending message to RASA
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        messages = loop.run_until_complete(self.agent.handle_text(user_message, sender_id=conversation_id))
        loop.close()

        #Deciphering RASA's response
        texts = []
        commands = []
        
        for message in messages:
            if 'text' in message:
                text = message['text']
                texts.append(text)
            elif 'custom' in message:
                commands.append(message['custom'])
        
        #Compiling responses
        response = {}
        response['text'] = texts
        response['commands'] = commands

        return response