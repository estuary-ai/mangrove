# Aegis-ML
*This repository hosts a server implementation hosting the Senva Digital Assistant backend, which is deployed on a local network connection to communicate in real-time with Hololens 2, serving as prototype for mixed reality solution for Astronauts SUITs; created as part of Team AEGIS project of University of Southern California (USC) with University of Arizona (UA) at the NASA-SUITs Competition 2022 *

## Main Modules are:
* Speech to Text (STTController.py)
* NLP + Dialogue Management (BotController.py)
* Text to Speech (TTSController.py)
* Hosting Server (main.py)

## Functionality:
To be revised and re-written.

## To run the server:
1. Make sure you install all dependancies `pip install -r requirements.txt` at a python 3.8 environment as well as CUDA 10.1 and cuDNN v8.05 (for GPU support). 
2. In one terminal/CMD tab, execute `python main.py` to run the Digital Assistant System. It is currently configured to run at localhost on port 4000.
3. Execute `rasa run actions` on another terminal/CMD tab to run RASA's action server which RASA running at `main.py` communicates with.
4. Run frontend project hosted possibly on Microsoft Hololens 2.



## API Format:
Please Look up the source code at `main.py` for SocketIO connections endpoints.
