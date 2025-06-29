from typing import Optional, List, Generator, Union, Callable, Dict
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
        self._stages_names: List[str] = [stage.__class__.__name__ for stage in stages] # TODO enumerate redundant types
        self._verbose = verbose
        self._on_ready_callback = lambda x: None
        self._host: 'DigitalAssistant' = None
    
    @property
    def response_emission_mapping(self) -> Dict[PipelineStage, Callable[[DataPacket], None]]:
        """Mapping of stages to their response emission functions"""
        return {}

    def add_stage(self, stage: PipelineStage, name: Optional[str] = None):
        self._stages.append(stage)
        if name is not None:
            stage.name = name
        else:
            stage.name = stage.__class__.__name__
        self._stages_names.append(stage.name)

    def _unpack(self):
        # NOT CALLED
        pass

    def _process(self, _):
        # NOT CALLED
        pass

    def on_start(self):
        def _build_on_ready_callback(
            stage: PipelineStage,
            next_stage: Optional[PipelineStage],
        ):
            def _callback(data_packet: Union[DataPacket, Generator[DataPacket, None, None]]):
                """Callback to be called when stage data is processed and ready to be fed to the next stage.
                Args:
                    data_packet (DataPacket or Generator[DataPacket, None]): Data packet to be fed to the next stage, or a generator of data packets.

                Raises:
                    ValueError: If data packet type does not match the expected type of the next stage.
                """
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


                # Emit response through host
                stage_name = self._stages_names[self._stages.index(stage)]
                if stage_name in self.response_emission_mapping:
                    logger.debug(f"Emitting response for {stage_name} through host")
                    self.response_emission_mapping[stage_name](data_packet)
                else:
                    pass  # No emission mapping defined for this stage

            return _callback

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