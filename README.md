
# Mangrove
Mangrove is the backend module of Estuary, a framework for building multimodal real-time Socially Intelligent Agents (SIAs).

## Supported Endpoints

### Speech-To-Text (STT/ASR)
* Faster-Whisper

### Large Language Models (LLMs)
* ChatGPT

### Text-To-Speech (TTS)
* ElevenLabs
* XTTS-v2
* Google gTTS
* pyttsx3


# Setup
## WSL Setup
If you already have Ubuntu 22.04 WSL installed on your machine, you can skip this section.  Otherwise, follow the steps below:
1. **[WSL Ubuntu 22.04]** Currently, Mangrove is tested to work in WSL Ubuntu 22.04.  To install WSL, follow this [official guide]((https://learn.microsoft.com/en-us/windows/wsl/install)) from Microsoft.
2. **[Updating WSL]** Run `sudo apt update` and `sudo apt upgrade` in WSL.
3. **[Installing pipx]** Run `sudo apt install pipx` in WSL.
4. **[Installing pdm]** Run `pipx install pdm` in WSL.

## Installing Dependencies
1. Install packages' dependencies for Ubuntu 22.04 - Tested on WSL2.
    ```bash
    sudo apt-get install libcairo2-dev pulseaudio portaudio19-dev libgirepository1.0-dev libespeak-dev sox ffmpeg gstreamer-1.0 clang
    ```
    
2. Install virtual environments manager
   <a href="https://www.anaconda.com/products/distribution" target="_blank">Anaconda</a>.

3. Create a python 3.9 virtual environment Using Conda or PDM as follows:
    ```bash
    pdm venv create 3.9
    pdm venv activate
   ```

4. Using `pdm use` ensure that pdm is pointing to the correct environment.

5. Install Python dependencies.
    ```bash
    pdm install -G :all
    ```

## Further Setup as Required
- If running in WSL and looking to communicate over LAN network, follow one of the methods mentioned [here](https://learn.microsoft.com/en-us/windows/wsl/networking).

- Running XTT (using Deepspeed) requires a standlone version of cuda library (the same version as the one used by `torch.version.cuda`).:
    1. Install `dkms` package to avoid issues with the installation of the cuda library: `sudo apt-get install dkms`
    2. Install CUDA 12.1 from the [NVIDIA website](https://developer.nvidia.com/cuda-12-1-0-download-archive?target_os=Linux&target_arch=x86_64&Distribution=WSL-Ubuntu&target_version=2.0&target_type=runfile_local).
    3. Follow the instructions given by the installation process including setting the PATH variables in the `.bashrc` file if on Ubuntu as follows:
        ```bash
        export PATH=/usr/local/cuda-12.1/bin${PATH:+:${PATH}}
        export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
        ```

- Mangrove currently supports the usage of APIs (e.g., OpenAI), which require API keys. Create `.env` file in the root directory of the project and add your API keys as follows:
    ```bash
    OPENAI_API_KEY=YOUR_API_KEY_FROM_OPENAI
    ELEVENLABS_API_KEY=YOUR_API_KEY_FROM_ELEVENLABS
    ```


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
