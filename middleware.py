#Simulating how the frontend can speak to the Rasa server directly by loading the model

import asyncio
from flask import Flask, request
import pyttsx3
import sys

from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig

agent = Agent.load("models/model.tar.gz", action_endpoint=EndpointConfig('http://localhost:5055/webhook'))
engine = pyttsx3.init()
engine.setProperty('rate', 120)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)

app = Flask(__name__)

if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@app.route("/", methods=["POST"])
def sendUserMessage():

    user_message = request.values.get('Body')
    conversation_id = request.values.get('From')

    if user_message == 'stop':
        return "End"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    messages = loop.run_until_complete(agent.handle_text(user_message, sender_id=conversation_id))
    loop.close()
    
    #Printing the response
    for message in messages:
        if 'text' in message:
            text = message['text']
            print (text)
            engine.save_to_file(text , 'output.wav')
            engine.runAndWait()
        elif 'custom' in message:
            print(message['custom'])

    return "Success"

if __name__ == '__main__':
    app.run()