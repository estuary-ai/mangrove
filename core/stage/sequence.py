from typing import Optional, List, Generator
from tqdm import tqdm

from core.utils import logger
from core.stage.base import PipelineStage
from core.data import DataPacket


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from server import DigitalAssistant


class PipelineSequence(PipelineStage):

    input_type = DataPacket
    output_type = DataPacket

    def __init__(
        self,
        stages: PipelineStage=[],
        verbose=False,
        **kwargs
    ):
        self._stages: List[PipelineStage] = stages
        self._verbose = verbose
        self._on_ready_callback = lambda x: None
        self._host: 'DigitalAssistant' = None

    def add_stage(self, stage: PipelineStage):
        self._stages.append(stage)

    def _unpack(self):
        # NOT CALLED
        pass

    def _process(self, _):
        # NOT CALLED
        pass

    def on_sleep(self):
        # NOT CALLED
        pass

    def on_start(self):
        def _build_on_ready_callback(
            stage: PipelineStage,
            next_stage: Optional[PipelineStage],
        ):
            def _callback(data_packet: DataPacket):
                from mangrove import STTStage, BotStage, TTSStage

                if not isinstance(data_packet, DataPacket):
                    logger.debug(f"Data packet is not a DataPacket, but a {type(data_packet)}, unpacking it")
                    assert isinstance(data_packet, Generator), f"Expected DataPacket or Generator, got {type(data_packet)}"
                    for dp in data_packet:
                        _callback(dp)
                    return

                if stage.is_interrupt_forward_pending():
                    import time
                    timestamp = int(time.time()) # TODO generate this timestamp in the beginning of the process of detecting the interrupt!
                    if next_stage is not None:
                        logger.warning(f"Stage {stage} issued interrupt signal, call interrupt of {next_stage}")    
                        # next_stage.signal_interrupt(timestamp) # TODO add this line back, after proper implementation
                    else:
                        logger.warning(f"Stage {stage} issued interrupt signal, no next stage to call")
                    self._host.emit_interrupt(timestamp)
                    stage.acknowledge_interrupt_forwarded()

                if next_stage is not None:
                    if not isinstance(data_packet, next_stage.input_type):
                        raise ValueError(f"Data packet type mismatch, expected {next_stage.input_type}, got {type(data_packet)}")

                    logger.trace(f"Feeding {data_packet} from {stage} to {next_stage}")

                        
                    next_stage.feed(data_packet)
                else:
                    logger.trace(f"Final stage in {self.__class__.__name__} reached, emitting response through host")

                if isinstance(stage, STTStage):
                    assert isinstance(data_packet, STTStage.output_type), f"Expected {STTStage.output_type}, got {type(data_packet)}"
                    self._host.emit_stt_response(data_packet)
                elif isinstance(stage, BotStage):
                    assert isinstance(data_packet, BotStage.output_type), f"Expected {BotStage.output_type}, got {type(data_packet)}"
                    self._host.emit_bot_response(data_packet)
                elif isinstance(stage, TTSStage):
                    assert isinstance(data_packet, TTSStage.output_type), f"Expected {TTSStage.output_type}, got {type(data_packet)}"
                    self._host.emit_bot_voice(data_packet)
                else:
                    logger.info(f"Unknown stage type {type(stage)}, not emitting response")    
                    # raise ValueError("Unknown Pipeline Stage Type")
            return lambda data_packet: _callback(data_packet)

        for stage, next_stage in zip(self._stages, self._stages[1:] + [None]):
            stage.on_ready_callback = _build_on_ready_callback(stage, next_stage)
            stage.start(host=self._host)

    def start(self, host):
        """Start processing thread"""
        logger.info(f'Starting {self}')
        self._host = host
        self.on_start()

    def feed(self, data_packet: DataPacket):
        if data_packet is None:
            return None
        if not isinstance(data_packet, self._stages[0].input_type):
            raise ValueError(f"Data packet type mismatch, expected {self._stages[0].input_type}, got {type(data_packet)}")
        self._stages[0].feed(data_packet)

    def on_connect(self):
        # Implementable
        pass

    def on_disconnect(self):
        # Implementable
        pass