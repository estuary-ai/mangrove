
# Mangrove
Mangrove is the backend module of Estuary, a framework for building multimodal real-time Socially Intelligent Agents (SIAs).

## Supported Endpoints

### Large Language Models (LLMs)
* ChatGPT

### Text-To-Speech (TTS)
* ElevenLabs
* XTTS-v2
* Google gTTS
* pyttsx3

# Setup

## Environment Setup

### WSL Setup
If you already have Ubuntu 22.04 WSL installed on your machine, you can skip this section.  Otherwise, follow the steps below:
1. **[WSL Ubuntu 22.04]** Currently, Mangrove is tested to work in WSL Ubuntu 22.04.  To install WSL, follow this [official guide]((https://learn.microsoft.com/en-us/windows/wsl/install)) from Microsoft.
2. **[Updating WSL]** Run `sudo apt update` and `sudo apt upgrade` in WSL.
3. **[Installing pipx]** Run `sudo apt install pipx`

### CUDA Library
**[CUDA 12.5.0]** Install CUDA 12.5.0 in your environment of choice e.g. if you would like to run Mangrove in WSL, follow the installation instructions in this [official guide](https://developer.nvidia.com/cuda-12-5-0-download-archive?target_os=Linux&target_arch=x86_64&Distribution=WSL-Ubuntu&target_version=2.0&target_type=deb_local) from NVIDIA.


## Installing Dependencies
1. Install virtual environments manager
   <a href="https://www.anaconda.com/products/distribution" target="_blank">Anaconda</a>.

2. Install PDM Package Manager:
    ```bash
    pipx install pdm
    ```

2. Create a python 3.9 virtual environment Using Conda or PDM.
    ```bash
    # Using PDM
    pdm venv create 3.9
    pdm venv activate

    # Or Using Conda
    conda create -n mangrove python=3.9
    conda activate mangrove
    ```

3. Using `pdm use` ensure that pdm is pointing to the correct environment.

4. Make sure to update conda forge.

   ```bash
   conda install -c conda-forge gcc=12.1.0
   ```

5. Install all dependancies:
    3.1 Install package dependencies for Ubuntu 22.04 - Tested on WSL2.

    ```bash
    sudo apt-get install libcairo2-dev pulseaudio portaudio19-dev libgirepository1.0-dev libespeak-dev sox ffmpeg gstreamer-1.0
    ```

    3.2 Install Python dependencies.

    ```bash
    pdm install
    ```

*NOTE:* If running in WSL and looking to communicate over LAN network, follow one of the methods mentioned [here](https://learn.microsoft.com/en-us/windows/wsl/networking).

## API Key Setup
Mangrove currently supports the usage of the follow APIs which can be added as path variables.  To do so, you may add the following to the end of your .bashrc file.

To edit the .bashrc file, you may use your preferred text editor e.g. `nano ~/.bashrc` or `code ~/.bashrc`.
* **[ChatGPT]:** `export OPENAI_API_KEY=`[key here]
* **[ElevenLabs]:** `export ELEVENLABS_API_KEY=`[key here]

# Acknowledgements
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
