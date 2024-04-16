# Traveller (Also known as Eva) - SENVA's Digital Assistant:
This repository hosts a server implementation hosting the **Senva Project** Digital Assistant (**Traveller**, previously called **Eva**) backend, which is typically deployed in a local network connection to communicate in real-time with Hololens 2, serving as prototype for mixed reality solution for Astronauts **SUITs**. It corresponds to the ongoing effort of **Team AEGIS** project at the **NASA-SUITs** Challenge in the following years:

- **2023**: **University of Southern California (USC)** with **University of Berkley (UCBerkley)**

- **2022**: **University of Southern California (USC)** with **University of Arizona (UA)**.


## Eva's Modules:

- Speech to Text (`STTController`) employing **Mozilla DeepSpeech v0.9.3** and **Porcupine Wake word engine** for Wake-Up word detection.
- Dialogue Management + Natural Language Processor (`BotController`) employing **Rasa v2.0.0**
- Text to Speech (`TTSController`) employing **pyttsx3** and **inflect**.
* `AssistantController`: contains logic of utilizing the above modules.
* `StorageManager`: singleton responsible for threading background files writing as well as logging end-points.
* Hosting `SocketIO` Server (`server.py`)



## Instructions to install:
1. Install virtual environments manager, preferably through
   <a href="https://www.anaconda.com/products/distribution" target="_blank">Anaconda</a>.

2. Create a python 3.9 virtual environment.
    ```
    conda create -n senva python=3.9
    conda activate senva
    ```

3. Install all Eva's libraries dependancies:
3.1 Install all Eva's libraries dependancies for Ubuntu 22.04.
    ```
    sudo apt-get install libcairo2-dev pulseaudio portaudio19-dev libgirepository1.0-dev libespeak-dev sox ffmpeg gstreamer-1.0
    ```

3.2 Install all Eva's libraries dependancies of python.
    ```
    pip install -r requirements.txt
    ```

3.3 If running in WSL and looking to communicate over LAN network, call the following command as an administrator in `cmd`/`powershell`:
    ```
    netsh interface portproxy add v4tov4 listenport=4000 listenaddress=0.0.0.0 connectport=4000 connectaddress=127.0.0.1
    # if it does not work, it might help to reset proxy with the following command:
    netsh interface portproxy reset all
    ```
    # Ensure that the following would show up when calling the following:
    netstat -ano | find '"4000"'
    ```
    TCP    0.0.0.0:4000           0.0.0.0:0              LISTENING       
    TCP    127.0.0.1:4000         0.0.0.0:0              LISTENING       
    ```


## Running Eva:
1. In one terminal tab, execute `python main.py` to run the Digital Assistant System. It is currently configured to run at localhost on port 4000.
2. Execute `rasa run actions` on another terminal/CMD tab to run RASA's action server which RASA running at `server.py` communicates with.
3. Run client hosted possibly on Microsoft Hololens 2 or any other client that can communicate with the server using SocketIO such as at `client/python/client.py`


## Checklist Of Extensions
- [ ] Update the below portion of the `README`
- [ ] Implement project `setup.py`
- [ ] Experiment using LLMs for intent handling
    - Options: [Bloom](https://towardsdatascience.com/run-bloom-the-largest-open-access-ai-model-on-your-desktop-computer-f48e1e2a9a32)
- [ ] Experiment using other opensource STTs.
    - Options: [Kaldi](https://github.com/kaldi-asr/kaldi), [Wav2letter](https://github.com/flashlight/flashlight/tree/main/flashlight/app/asr), [DeepSpeech](https://github.com/mozilla/DeepSpeech)


## Functionality (Not Updated):
We have tied together these components in a script that runs on the server and starts a connection using SocketIO over Flask. Our built connection supports a few events, which when appropriately utilized activate the digital assistant.

### **Main supported listening events are:**

> `stream-wakeup`: Receiving a stream of audio bytes, it emits back an acknowledgement once the wake up word is detected.

> `stream-audio`: Receiving a stream of audio bytes, it emits speech transcription upon detection of an amount of speech audio bytes followed by momentarily silence (Fixed scenarios differ). Consequently emits another Json object defining the Bot response including textual response, supported commands if applicable (See below), and a wav file of audible form of the textual response of the Assistant.

> `reset-audio-stream`: Resets stream-audio recent stream line.

> `read-tts`: Upon receiving data values, the source name, and optionally their corresponding units, it emits a wav file corresponding to an audible statement of reading the data.


### **Main supported emitting events are:**

> `wake-up`: Acknowledges detection of the wake-up word in a sequence of audio bytes on stream-wakup.

> `stt-response`: Emits the transcription of speech detected in a sequence of audio bytes transmitted on stream-audio.

> `bot-voice`:  Emits audio wav file corresponding to Eva’s voice.
bot-response: Emits as JSON object, Eva’s dialogue management response as to prior transcription.


## Client-Server Protocol:

Listening and Emitting to this set of supported events in an appropriate order from a SocketIO client, such as in Unity client for the Hololens, builds the behavior of a fully integrated Digital-Assistant. Eva’s supported patterns of commands can be viewed as three generic classes of commands; these are one shot commands, purpose scenarios commands, and data reading commands.

Adapted basic scenario order goes as follows which regularly initiates any of the classes’:


> 1. Continuously emitting to `stream-wakeup` a stream of audio bytes.
>
> 2. **If the wake-up word is detected**, switch audio stream emission and start instead a continuous stream to `stream-audio`.
>
> 3. Now the Digital Assistant is listening, and as soon as some speech followed by momentarily silence is detected, corresponding transcription is emitted on `stt-response`, followed by Eva’s response to what the user said as JSON object (Description) on `bot-response`, and wav audio corresponding to the audible form of human readable textual response (if any available) by Eva on `bot-voice`.
>
> 4. `bot-voice` emitted wav file shall be played on the client side.
>
> 5. Upon receiving `stt-response`, switch stream and go back to step 1, then Emit on `reset-audio-stream`.

If **one-shot commands** or not understood commands are provided, the scenario continues as follows:

> 6. `bot-response` emitted JSON objects shall be extracted and mapped to the appropriate functions such as ones responsible for manipulating units of the user interface.

If **data reading commands** are provided, the scenario continues as follows:

> 6. `bot-response` emitted JSON objects shall be extracted and mapped to the appropriate functions to extract data information corresponding to the detected feature in the response.
>
> 7. Emit on `stt-read`, the current values of the mentioned feature with corresponding feature.
>
> 8. Play audio wav file received on `bot-voice`.

If purpose scenarios command are provided, both servers and client have to understand that the system is getting into a series of question answer conversation, hence the scenario continues as follows:

> 6. `bot-response` emitted JSON objects shall be extracted and mapped to the appropriate functions to acknowledge purpose scenario command initiation, overriding **step 5**, by continuously emitting the audio bytes on `stream-audio`.
>
> 7. Depending on the purpose scenario, for example or currently supported Geology Sampling Scenario”, Eva would be waiting for the word “over” by the end of the sentence followed by a momentarily silence instead of the usual latter alone. Hence leaving time and flexibility to respond properly.
>
> 8. During the series of questions by the Dialogue Manager the statement is terminated by the user according to **step 7**, Listening on `bot-voice`, Eva’s response to the user statement or next question would come in audible form as well as in textual form on `bot-response`.
>
> 9. Listening to `bot-response` extracting any available commands encoding continuously, the client responds if needed with any related metadata such captured image, and geolocation data.
>
> 10. On the appropriate extracted command referring to purpose scenario termination, the client understands the status of the scenario including the termination, accordingly switches audio stream and goes back to **step 1**.
