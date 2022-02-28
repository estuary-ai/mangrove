#Simulating how the frontend can speak to the Rasa server directly using API calls

import requests

#Checking whether the rasa server is running
try:
    response = requests.get('http://localhost:5005/')
    if response.status_code != 200:
        print('Error: RASA server might not be available')
        exit()
except:
    print('Error: RASA server might not be available')
    exit()

conversation_id = '123'

while True:

    #Get user input
    user_message = input('Enter: ')
    if user_message == 'q':
        break

    #Getting the intent
    response = requests.post('http://localhost:5005/model/parse', json = {'text': user_message, 'message_id': conversation_id})
    intent = response.json()['intent']['name']
    confidence = response.json()['intent']['confidence']
    entities = {}
    for i in response.json()['entities']:
        entities[i['entity']] = i['value']

    #Fallback condition where the confidence is less than 0.5
    if confidence < 0.5:
        response = requests.post(f'http://localhost:5005/conversations/{conversation_id}/trigger_intent', json = {'name': '/fallback', 'entities': entities})
    else:
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