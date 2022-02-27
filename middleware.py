#Flask app to receive messages from frontend

from flask import Flask, request
import requests

app = Flask(__name__)

@app.route("/", methods=["POST"])
def sendUserMessage():

    user_message = request.values.get('Body')
    conversation_id = request.values.get('From')

    #Getting the intent
    response = requests.post('http://localhost:5005/model/parse', json = {'text': user_message, 'message_id': conversation_id})
    intent = response.json()['intent']['name']
    confidence = response.json()['intent']['confidence']
    entities = {}
    for i in response.json()['entities']:
        entities[i['entity']] = i['value']

    print(intent, confidence)

    #Working on the intent
    response = requests.post(f'http://localhost:5005/conversations/{conversation_id}/trigger_intent', json = {'name': intent, 'entities': entities})
    messages = response.json()['messages']
    
    #Printing the response
    for message in messages:
        if 'text' in message:
            print (message['text'])
        if 'image' in message:
            print(message['image'])
        if 'custom' in message:
            print(message['custom'])

    return "Success"

if __name__ == '__main__':
    #Checking whether the rasa server is running
    try:
        response = requests.get('http://localhost:5005/')
        if response.status_code != 200:
            print('Error: RASA server might not be available')
            exit()
    except:
        print('Error: RASA server might not be available')
        exit()

    app.run()