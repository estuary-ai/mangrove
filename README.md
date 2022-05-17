# Aegis-ML
*This repository hosts a server implementation hosting the Senva Digital Assistant backend, which is deployed on a local network connection to communicate in real-time with Hololens 2, serving as prototype for mixed reality solution for Astronauts SUITs; created as part of Team AEGIS project of University of Southern California (USC) with University of Arizona (UA) at the NASA-SUITs Competition 2022 *

## Main Modules are:
* Speech to Text (STTController.py)
* NLP + Dialogue Management (BotController.py)
* Text to Speech (TTSController.py)
* Hosting Server (main.py)
## Functionality:
The RASA model is able to handle the following types of requests from the user:
* Clicking on the screen
* Decluttering the screen
* Hiding/Showing panels such as heart rate, temperature, etc
* Toggling features (such as headlights and fans) on and off

## To run the server:
1. In one terminal/CMD tab, execute `python middleware.py` to run the trained RASA model. It is currently configured to run at localhost on port 5000.
2. Execute `rasa run actions` on another terminal/CMD tab to run RASA's action server.
3. Run `python frontend.py` to simulate requests from the Hololens. (Optional)

## API Format:
Request:
```json http
{
  "method": "POST",
  "url": "https://localhost:5000/",
  "data": {
        "Body": "text", 
        "From": "Neil"
    }
}
```

Response:
```
Success
```
> TODO: Configure text/speech data to be returned to Hololens