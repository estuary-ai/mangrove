#Simulating how the frontend can speak to the Rasa server directly by loading the model

import asyncio
import pyttsx3

from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig

agent = Agent.load("models/20220312-161232-cyan-limit.tar.gz", action_endpoint=EndpointConfig('http://localhost:5055/webhook'))
engine = pyttsx3.init()
engine.setProperty('rate', 120)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)

while True:

    user_message = input('Enter: ')
    if user_message == 'stop':
        break

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    messages = loop.run_until_complete(agent.handle_text(user_message))
    loop.close()
    
    #Printing the response
    for message in messages:
        if 'text' in message:
            text = message['text']
            print (text)
            engine.say(text)
            engine.runAndWait()
        if 'image' in message:
            print(message['image'])
        if 'custom' in message:
            print(message['custom'])