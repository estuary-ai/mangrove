import time
import threading                                                                
import functools                                                                
import collections

import webrtcvad
import deepspeech
import numpy as np
import sounddevice as sd                                         
from stt.FocusLevel import FocusLevel, init_words_focus_assets

def synchronized(wrapped):                                                      
    lock = threading.Lock()                                                     
    # print(lock, id(lock))                                                        
    @functools.wraps(wrapped)                                                   
    def _wrap(*args, **kwargs):                                                 
        with lock:                                                              
            # print ("Calling '%s' with Lock %s from thread %s [%s]"              
            #        % (wrapped.__name__, id(lock),                               
            #        threading.current_thread().name, time.time()))               
            result = wrapped(*args, **kwargs)                                   
            # print ("Done '%s' with Lock %s from thread %s [%s]"                 
            #        % (wrapped.__name__, id(lock),                               
            #        threading.current_thread().name, time.time()))               
            return result                                                       
    return _wrap  
    
class STTController:
    def __init__(self, 
                 sample_rate=16000,
                 model_path='models/ds-model/deepspeech-0.9.3-models',
                 load_scorer=True,
                 silence_threshold=200,
                 vad_aggressiveness=3,
                 frame_size=320,
                 verbose=False):
        
        self.frame_size = frame_size
        self.SAMPLE_RATE = sample_rate
        self.model = deepspeech.Model(model_path + ".pbmm")
        if load_scorer:
            self.model.enableExternalScorer(model_path + ".scorer")

        self.buffered_data = b""
        # ms of inactivity at the end of the command before processing
        self.SILENCE_THRESHOLD = (silence_threshold//10)*320*2
        self.silence_buffers = collections.deque(maxlen=2)
        self.silence_start = None
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.verbose=verbose

        # self.is_stream_locked = False

        self.debug_total = 0
        self.debug_silence = 0
        self.debug_voice = 0
        self.debug_feed = 0
        self.debug_silence_state = 0

        self.init_words_focus_assets()


    def feed_silence(self, num_samples=320*3):
        data = b'\x00\x00'*num_samples
        self.stream_context.feedAudioContent(np.frombuffer(data, np.int16))
        
        
    def create_stream(self):
        self.stream_context = self.model.createStream()
        self.feed_silence()
        self.recorded_chunks = 0
        self.recorded_audio_length = 0
        self.debug_data_feed = b''


    def remove_focus(self):
        self.model.clearHotWords()

    def is_stream_context_running(self):
        return (self.stream_context is not None)

    # @synchronized
    def _finish_stream(self):
        if self.stream_context is not None:
            # self.is_stream_locked = True
            print("Processing stream", end="\n", flush=True)
            # self._process_data_buffer()
            start = round(time.time() * 1000)
            
            self.feed_silence()
            transcription = self.stream_context.intermediateDecode()

            if transcription:
                # TODO lock stream and ditch everything unless stream is unlocked back
                # sd.play(np.frombuffer(self.debug_data_feed, dtype=np.int16), 16000)
                # sd.wait()
                # with open(f"../sample-audio-binary/{transcription}_{str(time.time())}.txt", mode='wb') as f:
                #     f.write(self.debug_data_feed)

                print( " " + str(transcription), end="\n", flush=True)
                self._log("Recognized Text:" +  str(transcription))
                recog_time = round(time.time() * 1000) - start

                self.reset_audio_stream()

                return { 
                    'text': transcription,
                    'recog_time': recog_time,
                    'recorded_audio_length': self.recorded_audio_length
                    }

        # with open(f'../sample-audio-binary/null_{str(time.time())}.txt', mode="wb") as f:
        #     f.write(self.debug_data_feed)

        # self.is_stream_locked = False
        # self.reset_audio_stream()

    # def unlock_stream(self):
    #     self.is_stream_locked = False

    def _add_buffered_silence(self, data):
        if len(self.silence_buffers) > 0:
            # DEBUG START
            for buf in self.silence_buffers:
                self.debug_feed -= len(buf)
            # DEBUG END
            self.silence_buffers.append(data)
            total_length = 0
            for buf in self.silence_buffers:
                total_length += len(buf)
            audio_buffer = b''.join(self.silence_buffers)
            self._reset_silence_buffer()
        else:
            audio_buffer = data
        return audio_buffer    

    def _reset_silence_buffer(self):
        self.silence_buffers = collections.deque(maxlen=2)
        
    def _feed_audio_content(self, data):
        self.debug_feed += len(data)
        self.recorded_audio_length += int((len(data)/2) * (1/self.SAMPLE_RATE) * 1000)
        self.debug_data_feed += data
        self.stream_context.feedAudioContent(np.frombuffer(data, np.int16))

    def _process_voice(self, data):
        self.silence_start = None
        if self.recorded_chunks == 0:
            self._log('\n[start]') # recording started
        else:
            self._log('=') # still recording
        self.recorded_chunks += 1
        data = self._add_buffered_silence(data)
        self._feed_audio_content(data)

    """
    Returns decoding in JSON format and reinit the stream
    """
    def _intermediate_decode(self):
        results = self._finish_stream()
        self.create_stream()
        return results


    # TODO make _process_silence using samples count or percentge
    #  instead of time
    def _process_silence(self, data):
        if self.recorded_chunks > 0: # recording is on
            self._log('-') # silence detected while recording
            self.debug_feed -= len(data)
            self._feed_audio_content(data)
            
            if self.silence_start is None:
                self.silence_start = self.debug_total
                # self.silence_start = round(time.time() * 1000)
            else:
                now = self.debug_total
                # now = round(time.time() * 1000)
                self.debug_silence_state = now - self.silence_start
                if (now - self.silence_start) >= self.SILENCE_THRESHOLD:
                    # print("catch", end="", flush=True)
                    self.silence_start = None
                    self._log("\n[end]")
                    results = self._intermediate_decode()
                    return results
        else:
            # VAD has a tendency to cut the first bit of audio data 
            # from the start of a recording
            # so keep a buffer of that first bit of audio and 
            # in addBufferedSilence() reattach it to the beginning of the recording
            self._log('.') # silence detected while not recording
            self.silence_buffers.append(data)
    
    @synchronized
    def process_audio_stream(self, new_data):         
        # if self.is_stream_locked:
        #     # buffer all incoming data if stream is locked
        #     # TODO automatically process them once stream is unlocked!
        #     self.buffered_data += new_data
        #     return
        
        data_stream = self.buffered_data + new_data 
        self._reset_data_buffer()
        
        outcomes = [] 
        i = 0
        while i < len(data_stream):
            sub_data = data_stream[i:i+self.frame_size]

            # Process only proper frame sizes
            if len(sub_data) < self.frame_size:
                break

            self.debug_total += len(sub_data)

            is_speech = self.vad.is_speech(sub_data, self.SAMPLE_RATE)
            if is_speech:
                self.debug_voice += len(sub_data)
                self._process_voice(sub_data)
            else:
                self.debug_silence += len(sub_data)
                result = self._process_silence(sub_data)
                if result is not None:
                    outcomes.append(result)


            i += self.frame_size
        
        self.buffered_data = data_stream[i:]

        if len(outcomes) > 0:
            return self._combine_outcomes(outcomes)
        

    def _combine_outcomes(self, outcomes):
        final = { 
                    'text': "",
                    'recog_time': 0,
                    'recorded_audio_length': 0
                }

        for result in outcomes:
            final["text"] += result["text"].strip()
            final["recog_time"] += result["recog_time"]
            final["recorded_audio_length"] += result["recorded_audio_length"]

        return final

        # // timeout after 1s of inactivity
        # clearTimeout(endTimeout);
        # endTimeout = setTimeout(function() {
        # 	console._log('timeout');
        # 	resetAudioStream();
        # },1000);


    # def _process_data_buffer(self):
    #     if len(self.buffered_data) > 0:
    #         print("process_data_buffer", len(self.buffered_data))
    #         self._feed_audio_content(self.buffered_data)
    #         # print("feeding buffered", len(self.buffered_data))
    #         self._reset_data_buffer()

    def reset_audio_stream(self):
        # clearTimeout(endTimeout)
        self._log('\n[reset]')

        self.create_stream()
        # self._intermediate_decode() # ignore results
        
        self.recorded_chunks = 0
        self.silence_start = None
        self.buffered_data = b""
        self._reset_data_buffer()
        self._reset_silence_buffer()

    def _reset_data_buffer(self):
        self.buffered_data = b""

    def _log(self, msg, end="", force=False):
        if self.verbose or force:
            print(msg, end=end, flush=True)

    def add_focus(self,
                words,
                boostValues=None,
                defaultBoost=FocusLevel.POS_MEDIUM.value):
        if boostValues is None:
            boostValues = [defaultBoost for _ in words]
        elif not isinstance(boostValues, list):
            if isinstance(boostValues, FocusLevel):
                boostValues = boostValues.value
            boostValues = [boostValues for _ in words]
            
        for word, boost in zip(words, boostValues):
            self.model.addHotWord(word, boost)

    def init_words_focus_assets(self):
        # print(len(init_words_focus_assets()))
        self.regular_neg_lo_focus,\
        self.regular_pos_lo_focus,\
        self.regular_pos_med_focus,\
        self.regular_pos_hi_focus,\
        self.tagging_med_focus,\
        self.tagging_hi_focus = init_words_focus_assets()
   
    def set_regular_focus(self):
        self.model.clearHotWords()
        self.add_focus(self.regular_pos_lo_focus, boostValues=FocusLevel.POS_LOW)
        self.add_focus(self.regular_pos_med_focus, boostValues=FocusLevel.POS_MEDIUM)
        self.add_focus(self.regular_pos_hi_focus, boostValues=FocusLevel.POS_HIGH)
        self.add_focus(self.regular_neg_lo_focus, boostValues=FocusLevel.NEG_LOW)
    
    def set_sample_tagging_focus(self):
        self.model.clearHotWords()
        self.set_regular_focus()
        self.add_focus(self.tagging_med_focus, boostValues=FocusLevel.POS_MEDIUM)
        self.add_focus(self.tagging_hi_focus, boostValues=FocusLevel.POS_HIGH)