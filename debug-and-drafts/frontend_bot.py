#Simulating how the frontend can call the Flask app
import sys
sys.path.insert(1, '../')
import requests

while True:
    #Get user input
    user_message = input('Enter: ')
    if user_message == 'q':
        break

    #Send message to server
    response = requests.post('http://localhost:5000/', data={'Body': user_message, 'From': '123'})
    print(response)