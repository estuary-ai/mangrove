
# Mangrove
Mangrove is the backend module of Estuary, a framework for builing multimodal real-time Socially Intelligent Agents (SIA).


## Instructions to install:
1. Install virtual environments manager, preferably through
   <a href="https://www.anaconda.com/products/distribution" target="_blank">Anaconda</a>.

2. Create a python 3.9 virtual environment.
    ```bash
    conda create -n mangrove python=3.9
    conda activate mangrove
    ```

3. Install all dependancies:
    3.1 Install package dependencies for Ubuntu 22.04 - Tested on WSL2.

    ```bash
    sudo apt-get install libcairo2-dev pulseaudio portaudio19-dev libgirepository1.0-dev libespeak-dev sox ffmpeg gstreamer-1.0
    ```

    3.2 Install Python dependencies.

    ```bash
    pip install -r requirements.txt
    ```

3.3 If running in WSL and looking to communicate over LAN network, follow one of the methods mentioned [here](https://learn.microsoft.com/en-us/windows/wsl/networking).


# Acknowledgements:
Mangrove was built from our base code of developing **Traveller**, the digital assistant of **SENVA**, a prototype Augmented Reality (AR) Heads-Up Display (HUD) solution for astronauts as part of the **NASA SUITs** Challenge. It corresponds to the effort of **Team AEGIS** project at the **NASA-SUITs** Challenge in the following years:

- **2023**: **University of Southern California (USC)** with **University of Berkley (UCBerkley)**

- **2022**: **University of Southern California (USC)** with **University of Arizona (UA)**.

The Estuary team would like to acknowledge the developers, authors, and creatives whose work contributed to the success of this project:

- SocketIO Protocol: https://socket.io/docs/v4/socket-io-protocol/
- FlaskSocketIO Library: https://github.com/miguelgrinberg/Flask-SocketIO
- Python SocketIO Library: https://github.com/miguelgrinberg/python-socketio
- Silero-VAD: https://github.com/snakers4/silero-vad
- Faster-Whisper: https://github.com/SYSTRAN/faster-whisper
- PyAudio: https://people.csail.mit.edu/hubert/pyaudio/
- TTS Library and [XTTs](https://arxiv.org/abs/2406.04904): https://github.com/coqui-ai/TTS


More to come soon! Stay tuned!
