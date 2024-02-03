#!/usr/bin/env python3
import time
import sys
import ffmpeg
import threading
import argparse
import queue
import sounddevice as sd
from loguru import logger
from stt.data_buffer import DataBuffer
from stt.audio_packet import AudioPacket


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


class RecordStream:
    # essential logic adapted from https://python-sounddevice.readthedocs.io/en/0.4.6/examples.html
    def __init__(self, data_buffer, url, blocksize):
        print("Setting up MicStream simulation from url")
        self.data_buffer = data_buffer
        self.url = url
        try:
            info = ffmpeg.probe(self.url)
        except ffmpeg.Error as e:
            sys.stderr.buffer.write(e.stderr)
            parser.exit(e)

        streams = info.get("streams", [])
        if len(streams) != 1:
            parser.exit("There must be exactly one stream available")

        stream = streams[0]

        if stream.get("codec_type") != "audio":
            parser.exit("The stream must be an audio stream")

        self.channels = stream["channels"]
        self.samplerate = float(stream["sample_rate"])

        self.blocksize = blocksize

        print(
            f"Recording  with {self.channels} channels and {self.samplerate} Hz samplerate ..."
        )

    def setup_readsize(self, reading_stream_samplesize):
        self.read_size = self.blocksize * self.channels * reading_stream_samplesize
        print(f"Setup read size: {self.read_size} bytes of audio!")

    def read_url_stream(self):
        def _read(self):
            process = (
                ffmpeg.input(self.url)
                .output(
                    "pipe:",
                    format="f32le",
                    acodec="pcm_f32le",
                    ac=self.channels,
                    ar=self.samplerate,
                    loglevel="quiet",
                )
                .run_async(pipe_stdout=True)
            )

            print("Starting Recording ...")
            prev_timestamp = 0
            while True:
                mic_chunk = process.stdout.read(self.read_size)
                if len(mic_chunk) == 0:
                    break
                audio_packet = AudioPacket(
                    {
                        "sampleRate": self.samplerate,
                        "numChannels": self.channels,
                        "timestamp": prev_timestamp,
                        "bytes": mic_chunk,
                    },
                )
                assert (
                    audio_packet.timestamp + audio_packet.duration >= prev_timestamp
                ), f"{audio_packet.timestamp} + {audio_packet.duration} < {prev_timestamp}"
                prev_timestamp = audio_packet.timestamp + audio_packet.duration
                self.data_buffer.put(audio_packet)
                # i+= 1
                # print(f'Put audio packet into buffer: {len(mic_chunk)} bytes')
                # print(f'Put audio packet into buffer: {i} packets')
                # print(f'Put audio packet into buffer: {len(mic_chunk)} bytes')
            print("Recording stopped")

        recording_thread = threading.Thread(target=_read, args=(self,))
        recording_thread.start()

        return recording_thread


class SpeakerStream:
    # essential logic adapted from https://python-sounddevice.readthedocs.io/en/0.4.6/examples.html

    def __init__(
        self, data_buffer: DataBuffer, blocksize, samplerate, channels, device
    ):
        print("Opening Speaker stream ...")
        self.data_buffer: DataBuffer = data_buffer
        self.blocksize = blocksize
        self.device = device
        self.reset_stream(samplerate, channels)

        from stt.stt_controller import STTController

        self.stt_controller = STTController()
        self.stt_controller.create_stream()

        print("Speaker stream opened")

        self.played_audio = AudioPacket.get_null_packet()
        self.num_played_packets = 0

    def reset_stream(self, samplerate=None, channels=None):
        if hasattr(self, "stream"):
            if self.stream.active:
                self.stream.stop()
            self.stream.close()

        self.samplerate = samplerate if samplerate is not None else self.samplerate
        self.channels = channels if channels is not None else self.channels
        self.stream = sd.RawOutputStream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            device=self.device,
            channels=self.channels,
            dtype="float32",
            callback=self.callback,
            finished_callback=self.finished_callback,
        )

    def finished_callback(self):
        # TODO something here
        # self.stream.close()
        print("Playback finished")

    def callback(self, outdata, frames, _time, status):
        assert frames == self.blocksize
        if status.output_underflow:
            print("Output underflow: increase blocksize?", file=sys.stderr)
            raise sd.CallbackAbort
        assert not status

        try:
            audio_packet = self.data_buffer.get(
                frame_size=self.blocksize * self.get_samplesize(), timeout=-1
            )
            self.stt_controller.feed(audio_packet)
            self.played_audio += audio_packet
            self.num_played_packets += 1
            audio_bytes = audio_packet.bytes
        except DataBuffer.Empty:
            audio_bytes = b"\x00" * len(outdata)  # silence
        except Exception as e:
            import traceback

            traceback.print_exc()
            print("Buffer is empty: increase buffersize?", file=sys.stderr)
            raise sd.CallbackAbort

        if len(audio_bytes) < len(outdata):
            # print(f'Audio buffer is not full: {len(audio_bytes)} < {len(outdata)}', file=sys.stderr)
            # outdata[:len(audio_bytes)] = audio_bytes
            # outdata[len(audio_bytes):].fill(0)
            raise sd.CallbackStop
        else:
            outdata[:] = audio_bytes

    def get_samplesize(self):
        return self.stream.samplesize

    def listen_to_playback(self):
        self.reset_stream()
        self.stream.start()

        # self.playing_thread = threading.Thread(target=_play)
        # self.playing_thread.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-l",
        "--list-devices",
        action="store_true",
        help="show list of audio devices and exit",
    )
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parser],
    )
    parser.add_argument("url", metavar="URL", help="stream URL")
    parser.add_argument(
        "-d",
        "--device",
        type=int_or_str,
        help="output device (numeric ID or substring)",
    )
    parser.add_argument(
        "-b",
        "--blocksize",
        type=int,
        default=1024,
        help="block size (default: %(default)s)",
    )
    parser.add_argument(
        "-q",
        "--buffersize",
        type=int,
        default=100,
        help="number of blocks used for buffering (default: %(default)s)",
    )
    args = parser.parse_args(remaining)

    if args.blocksize == 0:
        parser.error("blocksize must not be zero")
    if args.buffersize < 1:
        parser.error("buffersize must be at least 1")

    try:
        data_buffer = DataBuffer(
            frame_size=args.blocksize, max_queue_size=args.buffersize
        )
        # q = queue.Queue(maxsize=args.buffersize)
        record_stream = RecordStream(data_buffer, args.url, args.blocksize)

        from stt.audio_packet import TARGET_SAMPLERATE

        listening_stream = SpeakerStream(
            data_buffer,
            args.blocksize,
            # 16000, 1, # 32000, 1,
            TARGET_SAMPLERATE,
            1,
            # record_stream.samplerate, 1, # record_stream.channels,
            args.device,
        )
        record_stream.setup_readsize(listening_stream.get_samplesize())

        while True:
            recording_thread = record_stream.read_url_stream()

            # create thread to call process_audio_buffer
            def _process_audio_buffer():
                import backoff

                logger.success("Processing audio buffer ...")
                complete_transcription = []
                while True:
                    # time.sleep(0.5)
                    if data_buffer.empty() and not recording_thread.is_alive():
                        logger.warning(
                            "No more audio packets in buffer, and recording thread is not alive anymore"
                        )
                        break

                    # print(f'number of played packets: {listening_stream.num_played_packets}')
                    @backoff.on_exception(backoff.expo, DataBuffer.Empty)
                    def _process_buffer():
                        return listening_stream.stt_controller.process_audio_buffer()

                    transcription = _process_buffer()
                    if transcription is not None:
                        logger.info(
                            f"Getting transcription ... as silence was detected"
                        )
                        logger.debug(f"Transcription: {transcription}")
                        complete_transcription.append(transcription)

                _str = ""
                for i, transcription in enumerate(complete_transcription):
                    _str += f"#{i}: {transcription}\n"
                logger.success(f"Complete transcription: {_str}")

            processing_thread = threading.Thread(target=_process_audio_buffer)
            processing_thread.start()

            listening_stream.listen_to_playback()

            logger.info("> Recording ...")
            while True:
                recording_thread.join(0.5)
                if not recording_thread.is_alive() and data_buffer.empty():
                    break
            logger.info("> Recording finished")

            logger.info(f"Waiting for processing thread to finish ...")
            while processing_thread.is_alive():
                processing_thread.join(0.1)

            logger.info(
                f"number of played packets: {listening_stream.num_played_packets}"
            )
            logger.success("Done processing audio buffer")
            logger.info("Force finishing stream ... (just in case)")
            transcription = listening_stream.stt_controller._finish_stream(
                force_clear_buffer=True
            )
            if transcription is not None:
                logger.info(f"Getting transcription ... if no silence was detected")
                logger.warning(f"Transcription: {transcription}")

            logger.info(
                f"number of played packets: {listening_stream.num_played_packets}"
            )
            logger.success("Done one recording")

            # print('> Recording ...')
            # while True:
            #     recording_thread.join(0.5)
            #     if not recording_thread.is_alive():
            #         break
            # print('> Recording finished')

            # frame_size = 512*4
            # audio_packets = []
            # while True:
            #     try:
            #         audio_packets.append(data_buffer.get(frame_size=frame_size, timeout=-1))
            #     except DataBuffer.Empty:
            #         break

            # import torch

            # device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            # model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
            #                   model='silero_vad',
            #                   force_reload=True,
            #                   onnx=False)
            # model.to(device)

            # (get_speech_timestamps,
            # save_audio,
            # read_audio,
            # VADIterator,
            # collect_chunks) = utils

            # vad_iterator = VADIterator(model)
            # # from webrtcvad import Vad
            # # vad = Vad(3)
            # # print('Checking for speech ...')
            # num_of_packets = len(audio_packets)
            # prev_speech=True
            # for i, audio_packet in enumerate(audio_packets):
            #     if len(audio_packet.bytes) < frame_size:
            #         print(f'Packet {i+1}/{num_of_packets} is too short: {len(audio_packet.bytes)} bytes')
            #         continue
            #     chunk = torch.tensor(audio_packet.float).to(device)
            #     speech_prob = model(chunk, audio_packet.sample_rate).item()
            #     if speech_prob > 0.9:
            #         print(f'Packet {i+1}/{num_of_packets} is speech: {speech_prob}')
            #     # speech_dict = vad_iterator(audio_packet_float, return_seconds=True)
            #     # if speech_dict:
            #     #     print(f'Packet {i+1}/{num_of_packets} is speech:\n {speech_dict}')
            #     # is_speech = vad.is_speech(audio_packet.bytes, audio_packet.sample_rate)
            #     # if not is_speech:
            #     #     if prev_speech:
            #     #         print(f'Packet {i+1}/{num_of_packets} is not speech')
            #     #     prev_speech=False
            #     # else:
            #     #     prev_speech=True
            # print('Done checking for speech')
            #     # print(f'is speech: {is_speech}')
            #     # if is_speech:
            #     #     listening_stream.stt_controller.feed(audio_packet)

            if input("Press Enter to start recording") == "q":
                break
        print("Waiting for last playback to finish ...")

    except KeyboardInterrupt:
        parser.exit(0, "\nInterrupted by user")
    except queue.Full:
        # A timeout occurred, i.e. there was an error in the callback
        parser.exit(1)
    except Exception as e:
        parser.exit(type(e).__name__ + ": " + str(e))
