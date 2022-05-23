import deepspeech
import numpy as np
import time
import sys
import collections
from sqlalchemy import false
import webrtcvad

from enum import Enum

import sounddevice as sd

class FocusLevel(Enum):
    POS_HIGH = 10.5
    POS_MEDIUM = 6.0
    POS_LOW = 1.0
    NEG_LOW = -1.0
    NEG_MEDIUM = -4.0
    NEG_HIGH = -9.0

class STTController:
    def __init__(self, 
                 sample_rate=16000,
                 model_path='models/ds-model/deepspeech-0.9.3-models',
                 load_scorer=True,
                 silence_threshold=300,
                 vad_aggressiveness=3,
                 frame_size = 320,
                 verbose=False):
        
        self.frame_size = frame_size
        self.SAMPLE_RATE = sample_rate
        self.model = deepspeech.Model(model_path + ".pbmm")
        if load_scorer:
            self.model.enableExternalScorer(model_path + ".scorer")

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
        self.debug_feed = 0
        self.debug_silence_state = 0
        self.debug_prev_debug_data_feed = b''

        self.init_words_focus_assets()

        
    def create_stream(self):
        self.stream_context = self.model.createStream()
        data = b'\x00\x00'*640
        self.stream_context.feedAudioContent(np.frombuffer(data, np.int16))
        self.recorded_chunks = 0
        self.recorded_audio_length = 0
        self.debug_data_feed = b''


    def remove_focus(self):
        self.model.clearHotWords()

    def is_stream_context_running(self):
        return (self.stream_context is not None)

    def finish_stream(self):
        
        print("Processing stream", end="\n", flush=True)
        self.is_feed_locked = True
        if self.stream_context is not None:
            # print("self.stream_context is good", end="", flush=True)
            start = round(time.time() * 1000)

            # include buffered data
            # self.process_data_buffer()

            transcription = self.stream_context.finishStream()
            # if not transcription:
            #     print( "no transcription:: " + str(transcription), flush=True)
            #     self.create_stream()
            #     self.feed_audio_content(self.debug_data_feed)
            #     transcription = self.stream_context.finishStream()

            if transcription:
                self.debug_prev_debug_data_feed = self.debug_data_feed
                # sd.play(np.frombuffer(self.debug_prev_debug_data_feed, dtype=np.int16), 16000)
                # sd.wait()
                # print( " " + str(transcription), end="", flush=True)
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
            self.reset_silence_buffer()
        else:
            audio_buffer = data
        return audio_buffer    

    def reset_silence_buffer(self):
        self.silence_buffers = collections.deque(maxlen=2)
        
    def feed_audio_content(self, data):
        self.debug_feed += len(data)
        self.recorded_audio_length += int((len(data)/2) * (1/self.SAMPLE_RATE) * 1000)
        self.debug_data_feed += data
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


    # TODO make process_silence using samples count or percentge
    #  instead of time
    def process_silence(self, data):
        if self.recorded_chunks > 0: # recording is on
            self.log('-') # silence detected while recording
            self.debug_feed -= len(data)
            self.feed_audio_content(data)
            
            if self.silence_start is None:
                self.silence_start = round(time.time() * 1000)
            else:
                now = round(time.time() * 1000)
                self.debug_silence_state = now - self.silence_start
                if (now - self.silence_start) > self.SILENCE_THRESHOLD:
                    # print("catch", end="", flush=True)
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
        data_stream = self.buffered_data + new_data 
        self.reset_data_buffer()
        
        outcomes = [] 
        i = 0
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
            print("process_data_buffer", len(self.buffered_data))
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
            print(msg, flush=True)

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
        self.regular_neg_lo_focus = [
            'lo', 'then', 'altaforte', 'generate', 'la',
            'stan', 'plate', 'his', 'her',
            'theology', 'once',
             # maybe not so much ->
            'and', 'leg', 'so', 'some', 'little', 'a',
            'simple', 'better',
        ]
        regular_pos_lo_focus = [
            'close',
            'hold',
            'turn', 'on', 'off',
            'rock', 'show', 'screen',
            'read',
            'measurement',
            'monitoring', 'heart', 
            'stand',
            'start', 'recording',
            'sub',
            'gas',
            'red',
        ]

        regular_pos_med_focus = [
            'heads', 'up', 'display', 'show',
            'hide', 'sample', 'tag', 'rate', 'rock',
            'respiratory', 'note', 'map',
            'battery',  'terrain',
            'green', 'blue', 'pin',
            'read', 'condition', 'suit',
            'path',  
            'checklist',
            'data', 
            'take', 'photo',
            'vitals',
            'audio',
            'toggle',
            'set', 'north',
            'finder',
            'geology', 'level', 
        ]

        regular_pos_hi_focus = [
            'map', 'terrain', 'battery', 'oxygen', 'rate',
            'pin', 'road',
        ]

        tagging_med_focus = [
            'measurement', 'rock', 'regolith', 'coordinates', 'sun',
            'shining', 'shine', 'visbility', 'outcrop', 'poor', 'optimal',
            'boulder', 'outskirts', 'crater', 'rim',
            'landslide', 'lava', 'flow', 'PSR', 'contacts', 'lithologies',
            'pick', 'hammer', 'tools', 'used', 'using', 'use',
            'fist-sized', 'fist', 'shape', 'dimension', 'measures', 'centimeters',
            'inches', 'chip off', 'chip', 'fragment', 'scoop', 'material',
            'range', 'appearance',
            'color', 'dark', 'gray', 'basalts', 'white', 'anorthosites', 'mottled',
            'breccias', 'black', 'green', 'glass', 'beads', 
            'appearance' , 'texture', 'fine', 'grained', 'coarse',
            'vesiculated', 'coherent', 'brecciated', 'friable',
            'make out', 'variety', 'clasts', 'shiny', 'ilmenite',
            'opaque', 'phases', 'initial', 'geologic', 
            'interpretation', 'origin', 'breccia', 'formed', 'impacts',
            'anorthosite', 'represents', 'Moon’s', 'primary', 'crust',
            'secondary', 'rock', 'over',
        ]
        tagging_hi_focus = [
            'volcanic', 'orange', 'exit'
        ]

        tmp = self.remove_from([regular_pos_lo_focus,
                                regular_pos_med_focus,
                                regular_pos_hi_focus])
        self.regular_pos_lo_focus = tmp[0]
        self.regular_pos_med_focus = tmp[1]
        self.regular_pos_hi_focus = tmp[2]

        tmp = self.remove_from([tagging_med_focus,
                                tagging_hi_focus,
                                regular_pos_lo_focus,
                                regular_pos_med_focus,
                                regular_pos_hi_focus])

        self.tagging_med_focus = tmp[0]
        self.tagging_hi_focus = tmp[1]




    def remove_from(self, lists):
        newListOfSets = []
        for i in range(len(lists)-1):
            othersSet = set()
            for other in lists[i+1:]:
                othersSet = othersSet.union(set(other))
            aSet = set(lists[i]).difference(othersSet)
            newListOfSets.append(aSet)
        newListOfSets.append(set(lists[-1]))
        return newListOfSets
        

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