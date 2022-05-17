import deepspeech
import numpy as np
import time
import sys
import collections
import webrtcvad

class STTController:

    def __init__(self, 
                 sample_rate=16000,
                 model_path='models/ds-model/deepspeech-0.9.3-models',
                 load_scorer=True,
                 silence_threshold=500,
                 vad_aggressiveness=1,
                 frame_size = 320,
                 verbose=False):
        
        self.frame_size = frame_size
        self.SAMPLE_RATE = sample_rate
        self.model = deepspeech.Model(model_path + ".pbmm")
        if load_scorer:
            self.model.enableExternalScorer(model_path + ".scorer")

        # self.model.addHotWord("sample", 15)

        self.buffered_data = b""

        # ms of inactivity at the end of the command before processing
        self.SILENCE_THRESHOLD = silence_threshold
        self.silence_buffers = collections.deque(maxlen=2)
        self.silence_start = None
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.verbose=verbose

        self.debug_total = 0
        self.debug_silence = 0
        self.debug_voice = 0

    def create_stream(self):
        self.stream_context = self.model.createStream()
        self.recorded_chunks = 0
        self.recorded_audio_length = 0

    def is_stream_context_running(self):
        return (self.stream_context is not None)

    def finish_stream(self):
        if self.stream_context:
            start = round(time.time() * 1000)

            # include buffered data
            self.process_data_buffer()

            transcription = self.stream_context.finishStream()
            if transcription:
                self.log("Recognized Text:" +  str(transcription))
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
            self.log('\n[start]') # recording started
        else:
            self.log('=') # still recording
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
            self.log('-') # silence detected while recording
            self.feed_audio_content(data)
            
            if self.silence_start is None:
                self.silence_start = round(time.time() * 1000)
            else:
                now = round(time.time() * 1000)
                if now - self.silence_start > self.SILENCE_THRESHOLD:
                    self.silence_start = None
                    self.log("\n[end]")
                    results = self.intermediate_decode()
                    return results
        else:
            # VAD has a tendency to cut the first bit of audio data 
            # from the start of a recording
            # so keep a buffer of that first bit of audio and 
            # in addBufferedSilence() reattach it to the beginning of the recording
            self.log('.') # silence detected while not recording
            self.silence_buffers.append(data)
            
    def process_audio_stream(self, new_data):         
        i = 0
        data_stream = self.buffered_data + new_data 
        outcomes = [] 
        while i < len(data_stream):
            sub_data = data_stream[i:i+self.frame_size]

            # Process only proper frame sizes
            if len(sub_data) < self.frame_size:
                break

            is_speech = self.vad.is_speech(sub_data, self.SAMPLE_RATE)
            if is_speech:
                self.debug_voice += len(sub_data)
                self.process_voice(sub_data)
            else:
                self.debug_silence += len(sub_data)
                result = self.process_silence(sub_data)
                if result is not None:
                    outcomes.append(result)

            i += self.frame_size
        
        self.buffered_data = data_stream[i:]

        if len(outcomes) > 0:
            self.process_data_buffer()
            return self._combine_outcomes(outcomes)
        

    def _combine_outcomes(self, outcomes):
        final = { 
                    'text': "",
                    'recog_time': 0,
                    'recorded_audio_length': 0
                }

        for result in outcomes:
            final["text"] += result["text"]
            final["recog_time"] += result["recog_time"]
            final["recorded_audio_length"] += result["recorded_audio_length"]

        return final

        # // timeout after 1s of inactivity
        # clearTimeout(endTimeout);
        # endTimeout = setTimeout(function() {
        # 	console.log('timeout');
        # 	resetAudioStream();
        # },1000);


    def process_data_buffer(self):
        if len(self.buffered_data) > 0:
            self.feed_audio_content(self.buffered_data)
            # print("feeding buffered", len(self.buffered_data))
            self.reset_data_buffer()

    def reset_audio_stream(self):
        # clearTimeout(endTimeout)
        self.log('\n[reset]')
        self.intermediate_decode() # ignore results
        self.recorded_chunks = 0
        self.silence_start = None
        self.buffered_data = b""
        self.reset_data_buffer()
        self.reset_silence_buffer()

    def reset_data_buffer(self):
        self.buffered_data = b""

    def log(self, msg, force=False):
        if self.verbose or force:
            sys.stdout.write(msg)