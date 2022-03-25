# Aegis-ML
*This repository hosts a server implementation where some ML-Tasks modules are deployed and will be communicating with the Hololens through a local network connection.*

## Modules are:
* Speech to Text Engine
* Natural Language Processor
* Dialogue Management Unit
* Text to Speech Engine

## To run the server:
1. In one terminal/CMD tab, execute `python middleware_loaded.py` to run the trained RASA model. It is currently configured to run at localhost on port 5000.
2. Execute `rasa run actions` on another terminal/CMD tab to run RASA's action server.
