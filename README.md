# Aegis-ML
*This repository hosts a server implementation where some ML-Tasks modules are deployed and will be communicating with the Hololens through a local network connection.*

## Modules are:
* Speech to Text Engine
* Natural Language Processor
* Dialogue Management Unit
* Text to Speech Engine

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