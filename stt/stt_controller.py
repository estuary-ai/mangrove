import time
import collections.abc
import numpy as np
import deepspeech
import webrtcvad
from functools import reduce
                                      
from storage_manager import StorageManager
from .focus_level import FocusLevel, init_words_focus_assets
from .data_buffer import DataBuffer
from .audio_packet import AudioPacket
from .vad_collector import vad_collector

class STTController:
    def __init__(self, 
                 sample_rate=16000,
                 model_path='models/ds-model/deepspeech-0.9.3-models',
                 load_scorer=True,
                 silence_threshold=200,
                 vad_aggressiveness=3,
                 frame_size=320,
                 verbose=True):
        
        self.frame_size = frame_size
        self.SAMPLE_RATE = sample_rate
        self.model = deepspeech.Model(model_path + ".pbmm")
        if load_scorer:
            self.model.enableExternalScorer(model_path + ".scorer")
        
        self.buffer = DataBuffer(self.frame_size)
        # ms of inactivity at the end of the command before processing
        self.SILENCE_THRESHOLD = silence_threshold #(silence_threshold//10)*320*2
        self.buffered_silences = collections.deque(maxlen=2)
        self.idx_silence_frame_start = None
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.verbose=verbose

        self.debug_total_size = 0
        self.debug_silence_size = 0
        self.debug_voice_size = 0
        self.debug_feed_size = 0
        self.debug_silence_size_state = 0

        # TODO
        self.init_words_focus_assets()

    def create_stream(self):
        def feed_silence(milliseconds=30):
            num_bytes = (milliseconds//10)*320
            silence_bytes = b'\x00\x00'*num_bytes
            self.stream_context.feedAudioContent(np.frombuffer(silence_bytes, np.int16))
        
        self.stream_context = self.model.createStream()        
        feed_silence()
        self.num_recorded_chunks = 0
        self.recorded_audio_length = 0
        self.debug_feed_frames = AudioPacket.get_null_packet()

    def _finish_stream(self):
        if self.stream_context is not None:
            self._log("\nTry to finalize Stream", end="\n", force=True)
            time_start_recog = round(time.time() * 1000)            
            transcription = self.stream_context.intermediateDecode()
            if transcription:
                # breakpoint() # TODO check meta data
                StorageManager.play_audio_packet(self.debug_feed_frames, transcription) # TODO Remove if not debugging
                
                self._log(f'Recognized Text: {transcription}', end="\n")
                recog_time = round(time.time() * 1000) - time_start_recog
                result = { 
                    'text': transcription,
                    'recog_time': recog_time,
                    'recorded_audio_length': self.recorded_audio_length
                }
                return result

        # with open(f'../sample-audio-binary/null_{str(time.time())}.txt', mode="wb") as f:
        #     f.write(self.debug_feed_frames)


    def _feed_audio_content(self, frame: AudioPacket):
        self.debug_feed_size += len(frame)
        self.recorded_audio_length += frame.duration
        self.debug_feed_frames += frame
        self.stream_context.feedAudioContent(np.frombuffer(frame.bytes, np.int16))

    def _process_voice(self, frame):
        def _concat_buffered_silence(frame):
            if len(self.buffered_silences) > 0:
                # if there were silence buffers append them
                # DEBUG START
                silence_len = reduce(lambda x, y: len(x) + len(y), self.buffered_silences)
                if isinstance(silence_len, AudioPacket):
                    silence_len = len(silence_len)
                self.debug_feed_size -= silence_len
                # DEBUG END
                self.buffered_silences.append(frame)
                complete_frame = reduce(lambda x, y: x+y, self.buffered_silences)
                self._reset_silence_buffer()
            else:
                complete_frame = frame
            return complete_frame    
        self.idx_silence_frame_start = None
        if self.num_recorded_chunks == 0:
            self._log('\n[start]', force=True) # recording started
        else:
            self._log('=') # still recording
        self.num_recorded_chunks += 1
        frame_inc_silence = _concat_buffered_silence(frame)
        self._feed_audio_content(frame_inc_silence)
    
    def _reset_silence_buffer(self):
        # TODO try increasing size
        self.buffered_silences = collections.deque(maxlen=2)

    # TODO make _process_silence using samples count or percentge instead of time
    def _process_silence(self, frame: AudioPacket):
        if self.num_recorded_chunks > 0: # recording is on
            self._log('-') # silence detected while recording
            self.debug_feed_size -= len(frame)
            self._feed_audio_content(frame)
            
            if self.idx_silence_frame_start is None:
                # self.idx_silence_frame_start = self.debug_total_size
                self.idx_silence_frame_start = frame.timestamp + frame.duration
                # self.idx_silence_frame_start = round(time.time() * 1000)
            else:
                # now = self.debug_total_size
                now = frame.timestamp + frame.duration
                # now = round(time.time() * 1000)
                self.debug_silence_size_state = now - self.idx_silence_frame_start
                if self.debug_silence_size_state >= self.SILENCE_THRESHOLD:
                    self.idx_silence_frame_start = None
                    self._log("\n[end]", force=True)                    
                    # Returns decoding in JSON format and reinit the stream                    
                    results = self._finish_stream()
                    self.create_stream()
                    return results
                
        else:
            # VAD has a tendency to cut the first bit of audio data 
            # from the start of a recording
            # so keep a buffer of that first bit of audio and 
            # in addBufferedSilence() reattach it to the beginning of the recording
            self._log('.') # silence detected while not recording
            self.buffered_silences.append(frame)
    
    def process_audio_stream(self, audio_packet):          
        freq = (3000//20)**320*2 # 3 seconds
        verbose_cond = (self.debug_total_size % freq) == 0
        verbose_cond &= (self.debug_total_size > freq)
        if verbose_cond:
            self._log(f'Verbose processing speech at {audio_packet.timestamp}', end="\n")
             
        self.buffer.add(audio_packet) 

    def process_audio_buffer(self):
        outcomes = [] 
        # Process only proper frame sizes
        for frame in self.buffer:
            self.debug_total_size += len(frame)
            is_speech = self.vad.is_speech(frame.bytes, self.SAMPLE_RATE)
            if is_speech:
                self.debug_voice_size += len(frame)
                self._process_voice(frame)
            else:
                self.debug_silence_size += len(frame)
                result = self._process_silence(frame)
                if result is not None:
                    outcomes.append(result)
    
        if len(outcomes) > 0:
            return self._combine_outcomes(outcomes)
    
    # def process_audio_buffer_new(self):
    #     while True:
    #         for bytes_segment in vad_collector(
    #             sample_rate=self.SAMPLE_RATE,
    #             frame_duration_ms=30, # TODO
    #             padding_duration_ms=300, # TODO
    #             vad=self.vad,
    #             frames=self.buffer
    #         ):
    #             audio = np.frombuffer(bytes_segment, dtype=np.int16)
    #             # TODO
    

    def _combine_outcomes(self, outcomes):
        merged_outcome = { 
            'text': "",
            'recog_time': 0,
            'recorded_audio_length': 0,
            'num_segments': 0
        }

        for result in outcomes:
            merged_outcome["text"] += result["text"].strip()
            merged_outcome["recog_time"] += result["recog_time"]
            merged_outcome["recorded_audio_length"] += result["recorded_audio_length"]
            merged_outcome['num_segments'] += 1
        return merged_outcome
    
    def reset_audio_stream(self):
        self._log('[reset]', end='\n')
        self.create_stream()        
        self.num_recorded_chunks = 0
        self.idx_silence_frame_start = None
        self._reset_silence_buffer()
        self.buffer.reset()

    def _log(self, msg, end="", force=False):
        if self.verbose or force:
            print(msg, end=end, flush=True)

    ###########################################################
    # Just focus methods
    ###########################################################
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
        
    def remove_focus(self):
        self.model.clearHotWords()
