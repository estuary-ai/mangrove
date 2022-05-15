import deepspeech
import numpy as np
import time
import sys
import collections
import webrtcvad

class STTController:

    def __init__(self):
        MODEL_PATH = 'ds-model/deepspeech-0.9.3-models'
        
        self.SAMPLE_RATE = 16000
        self.model = deepspeech.Model(MODEL_PATH + ".pbmm")
        self.model.enableExternalScorer(MODEL_PATH + ".scorer")

        # ms of inactivity at the end of the command before processing
        self.SILENCE_THRESHOLD = 300
        self.silence_buffers = collections.deque(maxlen=2)
        self.silence_start = None
        VAD_AGGRESSIVENESS = 1
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    def create_stream(self):
        self.stream_context = self.model.createStream()
        self.recorded_chunks = 0
        self.recorded_audio_length = 0

    def is_stream_context_running(self):
        return (self.stream_context is not None)

    def finish_stream(self):
        if self.stream_context:
            start = round(time.time() * 1000)
            transcription = self.stream_context.finishStream()
            if transcription:
                sys.stdout.write("")
                sys.stdout.write("Recognized Text:" +  str(transcription))
                recog_time = round(time.time() * 1000) - start
                return { 
                    'text': transcription,
                    'recog_time': recog_time,
                    'recorded_audio_length': self.recorded_audio_length
                    }
        self.reset_silence_buffer()
        self.stream_context = None

    def add_buffered_silence(self, data):
        if len(self.silence_buffers):
            self.silence_buffers.append(data)
            total_length = 0
            for buf in self.silence_buffers:
                total_length += len(buf)
            audio_buffer = b''.join(self.silence_buffers)
            self.reset_silence_buffer()
        else:
            audio_buffer = data
        return audio_buffer    

    def reset_silence_buffer(self):
        self.silence_buffers = collections.deque(maxlen=2)
        
    def feed_audio_content(self, data):
        self.recorded_audio_length += int((len(data)/2) * (1/self.SAMPLE_RATE) * 1000)
        self.stream_context.feedAudioContent(np.frombuffer(data, np.int16))

    def process_voice(self, data):
        self.silence_start = None
        if self.recorded_chunks == 0:
            sys.stdout.write('\n[start]') # recording started
        else:
            sys.stdout.write('=') # still recording
        self.recorded_chunks += 1
        data = self.add_buffered_silence(data)
        self.feed_audio_content(data)

    """
    Returns decoding in JSON format and reinit the stream
    """
    def intermediate_decode(self):
        results = self.finish_stream()
        self.create_stream()
        return results

    def process_silence(self, data):
        if self.recorded_chunks > 0: # recording is on
            sys.stdout.write('-') # silence detected while recording
            self.feed_audio_content(data)
            
            if self.silence_start is None:
                self.silence_start = round(time.time() * 1000)
            else:
                now = round(time.time() * 1000)
                if now - self.silence_start > self.SILENCE_THRESHOLD:
                    self.silence_start = None
                    sys.stdout.write("\n[end]")
                    results = self.intermediate_decode()
                    return results
        else:
            # VAD has a tendency to cut the first bit of audio data 
            # from the start of a recording
            # so keep a buffer of that first bit of audio and 
            # in addBufferedSilence() reattach it to the beginning of the recording
            sys.stdout.write('.') # silence detected while not recording
            self.silence_buffers.append(data)
            
    def process_audio_stream(self, data):
        # print(len(data))
        is_speech = self.vad.is_speech(data, self.SAMPLE_RATE)
        if is_speech:
            self.process_voice(data)
        else:
            return self.process_silence(data)

        # // timeout after 1s of inactivity
        # clearTimeout(endTimeout);
        # endTimeout = setTimeout(function() {
        # 	console.log('timeout');
        # 	resetAudioStream();
        # },1000);

    def reset_audio_stream(self):
        # clearTimeout(endTimeout)
        sys.stdout.write('\n[reset]')
        self.intermediate_decode() # ignore results
        self.recorded_chunks = 0
        self.silence_start = None