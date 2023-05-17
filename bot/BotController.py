import asyncio
import sys

from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig

from .procedures import EgressProcedure

class BotController:

    def __init__(self,
                 model_path='models/rasa-model/20230516-204842.tar.gz',
                 endpoint_config_address='http://localhost:5055/webhook'):
        
        self.egress_procedure = EgressProcedure()
        print("Loading RASA Agent...")
        self.agent =\
            Agent.load(model_path, action_endpoint=EndpointConfig(endpoint_config_address))
        print("Initialized RASA Agent")
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

        print(messages)

        #Deciphering RASA's response
        texts = []
        commands = []

        for message in messages:
            if 'text' in message:
                text = message['text']
                texts.append(text)
            elif 'custom' in message:
                command = message['custom']
                if command['target'] == 'UIA':
                    if command['action'] == 'start':
                        # reset the egress procedure
                        self.egress_procedure.restart()
                        # start video stream
                        # open egress checklist
                        commands.append({ 'target': 'UIA', 'action': 'open', 'additionalInfo': [] })
                        # set world state to egress in progress
                    elif command['action'] == 'next_step':
                        next_step = self.egress_procedure.get_next_step()
                        if next_step is None:
                            command['additionalInfo'] = ['-1', 'null']
                            texts.append('Completed all steps in procedure')
                        else:
                            command['additionalInfo'] = [next_step.stepId, next_step.target]
                            texts.append(next_step.text)
                        commands.append(command)
                else:
                    commands.append(command)
        
        #Compiling responses
        response = {}
        response['text'] = texts
        response['commands'] = commands

        print(commands)

        # Flatten commands
        # for command in commands:
        #     for key in command.keys():
        #         response['commands'][0][key] = str(command[key])

        return response