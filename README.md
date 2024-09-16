
# Mangrove
Mangrove is the backend module of Estuary, a framework for building multimodal real-time Socially Intelligent Agents (SIAs).

## Give us a Star! ⭐
If you find Estuary helpful, please give us a star!  Your support means a lot! 
If you find any bugs or would like to request a new feature, feel free to open an
issue!

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
   [copy and paste the output line to activate the environment]
   ```

4. Using `pdm use` ensure that pdm is pointing to the correct environment.

5. Install Python dependencies.
    ```bash
    pdm install -G :all
    ```

## Further Setup as Required

### Networked Configuration

If you are running Mangrove in WSL and would like to configure Local Area Network (LAN) communications for a remote client, WSL must be set to mirrored network configuration.  You can do this with the following steps:

1. Open Powershell and create/open the .wslconfig file in the `C:\Users\[username]\` directory.
2. Add the following to the .wslconfig file:
```bash
[wsl2]
networkingMode=mirrored
[experimental] 
dnsTunneling=true
autoProxy=true
hostAddressLoopback=true
```

#### Tips

- Ensure both Mangrove and the client are connected to the same LAN and both the machine running Mangrove and the LAN allow for device-to-device communications.
  
- [OPTIONAL] You may refer to the Microsoft WSL documentation on Mirrored Networking [here](https://learn.microsoft.com/en-us/windows/wsl/networking#mirrored-mode-networking).

### XTTS
- Running XTTS (using Deepspeed) requires a standlone version of cuda library (the same version as the one used by `torch.version.cuda`):
    1. Install `dkms` package to avoid issues with the installation of the cuda library: `sudo apt-get install dkms`
    2. Install CUDA 12.1 from the [NVIDIA website](https://developer.nvidia.com/cuda-12-1-0-download-archive?target_os=Linux&target_arch=x86_64&Distribution=WSL-Ubuntu&target_version=2.0&target_type=runfile_local).
    3. Follow the instructions given by the installation process including setting the PATH variables in the `.bashrc` file if on Ubuntu.  Add the following to the .bashrc file with any code editor ie. `nano ~/.bashrc`
        ```bash
        export PATH=/usr/local/cuda-12.1/bin${PATH:+:${PATH}}
        export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
        ```

### API Keys
- Mangrove currently supports the usage of APIs (e.g., OpenAI), which require API keys. Create `.env` file in the root directory of the project and add your API keys as follows:
    ```bash
    OPENAI_API_KEY=[your OpenAI API Key]
    ELEVENLABS_API_KEY=[your ElevenLabs API Key]
    ```


# Acknowledgements
Mangrove was built from our base code of developing **Traveller**, the digital assistant of **SENVA**, a prototype Augmented Reality (AR) Heads-Up Display (HUD) solution for astronauts.  Thank you to **Team Aegis** for participating in the **NASA SUITs Challenge** for the following years:

- **2023**: **University of Southern California (USC)** with **University of Berkley (UCBerkley)**

- **2022**: **University of Southern California (USC)** with **University of Arizona (UA)**.

The Estuary team would also like to acknowledge the developers, authors, and creatives whose work contributed to the success of this project:

- SocketIO Protocol: https://socket.io/docs/v4/socket-io-protocol/
- FlaskSocketIO Library: https://github.com/miguelgrinberg/Flask-SocketIO
- Python SocketIO Library: https://github.com/miguelgrinberg/python-socketio
- Silero-VAD: https://github.com/snakers4/silero-vad
- Faster-Whisper: https://github.com/SYSTRAN/faster-whisper
- PyAudio: https://people.csail.mit.edu/hubert/pyaudio/
- [XTTs](https://arxiv.org/abs/2406.04904): https://github.com/coqui-ai/TTS

More to come soon! Stay tuned and Fight On!
