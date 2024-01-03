#!/usr/bin/env python3

# NOTE: this example requires PyAudio because it uses the Microphone class

import time
import speech_recognition as sr


#!/usr/bin/env python
from ctypes import *
import pyaudio

# From alsa-lib Git 3fd4ab9be0db7c7430ebd258f2717a976381715d
# $ grep -rn snd_lib_error_handler_t
# include/error.h:59:typedef void (*snd_lib_error_handler_t)(const char *file, int line, const char *function, int err, const char *fmt, ...) /* __attribute__ ((format (printf, 5, 6))) */;
# Define our error handler type
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)


def py_error_handler(filename, line, function, err, fmt):
    pass


c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

asound = cdll.LoadLibrary("libasound.so")
# Set error handler
asound.snd_lib_error_set_handler(c_error_handler)


# this is called from the background thread
def callback(recognizer, audio):
    # received audio data, now we'll recognize it using Google Speech Recognition
    print("Received audio")
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)`
        print(
            "WHISPER Recognition thinks you said "
            + recognizer.recognize_whisper(audio, model="tiny.en")
        )
    except sr.UnknownValueError:
        print("WHISPER Recognition could not understand audio")
    except sr.RequestError as e:
        print(
            "Could not request results from WHISPER Recognition service; {0}".format(e)
        )


print("Starting...")

r = sr.Recognizer()
m = sr.Microphone()
with m as source:
    r.adjust_for_ambient_noise(
        source
    )  # we only need to calibrate once, before we start listening

print("Listening...")
# start listening in the background (note that we don't have to do this inside a `with` statement)
stop_listening = r.listen_in_background(m, callback)
# `stop_listening` is now a function that, when called, stops background listening
print("Listening...")

# do some unrelated computations for 5 seconds
for _ in range(50):
    time.sleep(
        0.1
    )  # we're still listening even though the main thread is doing other things
print("Listening...")

# calling this function requests that the background listener stop listening
stop_listening(wait_for_stop=False)
print("Stopped...")
# do some more unrelated things
while True:
    time.sleep(
        0.1
    )  # we're not listening anymore, even though the background thread might still be running for a second or two while cleaning up and stopping
