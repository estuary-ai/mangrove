from typing import Optional, List, Generator, Union, Callable, Dict
from core.utils import logger
from core.stage.base import PipelineStage
from core.data import AudioBuffer, DataBuffer, AudioPacket, DataPacket

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from server import DigitalAssistant

class PipelineSequence(PipelineStage):

    input_type = DataPacket
    output_type = DataPacket

    def __init__(
        self,
        name: str,
        stages: PipelineStage=[],
        verbose=False,
        **kwargs
    ):
        super().__init__(name=name, **kwargs)
        self._stages: List[PipelineStage] = stages
        self._verbose = verbose
        self._on_ready_callback = lambda x: None
        self._host: 'DigitalAssistant' = None
    
    @property
    def response_emission_mapping(self) -> Dict[PipelineStage, Callable[[DataPacket], None]]:
        """Mapping of stages to their response emission functions"""
        return {}

    def add_stage(self, stage: PipelineStage):
        self._stages.append(stage)
        # ensure the new stage has a unique name
        if stage.name in [s.name for s in self._stages[:-1]]:
            raise ValueError(f"Stage with name {stage.name} already exists in the pipeline sequence")

    def unpack(self):
        # NOT CALLED
        pass

    def process(self, _) -> None:
        # NOT CALLED
        pass

    def on_start(self):
        """Setting up the pipeline sequence"""
        input_stage = self._stages[0]
        if input_stage.input_type == AudioPacket: # it is an AudioToAnyStage
            logger.info(f"Initializing input buffer for {input_stage}")
            assert hasattr(input_stage, 'frame_size'), f"Input stage {input_stage} must have frame_size attribute"
            # the pipeline and the first stage share the same input buffer
            self.input_buffer = AudioBuffer(frame_size=input_stage.frame_size) # Created on the fly for the first stage
            input_stage.input_buffer = self.input_buffer

        assert self._stages[0].input_buffer is not None, f"Input buffer for the first stage {self._stages[0]} must be set before starting the pipeline sequence"

        for stage, next_stage in zip(self._stages, self._stages[1:]):
            assert stage.output_type == next_stage.input_type, f"Output type of stage {stage} must match input type of next stage {next_stage}"
            logger.info(f"Connecting stage {stage} to next stage {next_stage}")
            if next_stage.input_type == AudioPacket: 
                assert stage.output_type == AudioPacket, f"Output type of stage {stage} must be AudioPacket to connect to next stage {next_stage}"
                assert hasattr(next_stage, 'frame_size'), f"Next stage {next_stage} must have frame_size attribute"
                logger.info(f"Setting output buffer frame size for {stage} to {next_stage.frame_size}")
                stage.output_buffer.set_frame_size(next_stage.frame_size)
            else:
                assert isinstance(stage.output_buffer, DataBuffer), f"Output buffer of stage {stage} must be DataBuffer to connect to next stage {next_stage}, got {type(stage.output_buffer)}, while next stage input type is {next_stage.input_type}"

            next_stage.input_buffer = stage.output_buffer

        # verify all input/output buffers are set correctly
        logger.info(f"Verifying input/output buffers for all stages in {self.__class__.__name__}")
        for stage in self._stages:
            if stage.input_type == AudioPacket:
                assert hasattr(stage, '_input_buffer'), f"Input buffer for stage {stage} must be set before starting the pipeline sequence"
                assert stage.input_buffer is not None, f"Input buffer for stage {stage} must not be None"
            else:
                assert isinstance(stage.input_buffer, DataBuffer), f"Input buffer for stage {stage} must be DataBuffer, got {type(stage.input_buffer)}"
            if stage.output_type == AudioPacket:
                assert hasattr(stage, 'output_buffer'), f"Output buffer for stage {stage} must be set before starting the pipeline sequence"
                assert stage.output_buffer is not None, f"Output buffer for stage {stage} must not be None"
            else:
                assert isinstance(stage.output_buffer, DataBuffer), f"Output buffer for stage {stage} must be DataBuffer, got {type(stage.output_buffer)}"
        logger.success(f"All stages in {self.__class__.__name__} have valid input/output buffers")
        
        for stage in self._stages:
            logger.info(f"Starting stage {stage} with input type {stage.input_type} and output type {stage.output_type}")
            # Set the on_ready_callback for each stage based on the response_emission_mapping
            # If a stage has a response emission mapping, use it
            if stage.name in self.response_emission_mapping:
                logger.debug(f"Setting up response emission for {stage.name}")
                stage.on_ready_callback = self.response_emission_mapping[stage.name]
            else:
                logger.debug(f"No response emission mapping defined for {stage.name}, using default callback")
            stage.start(host=self._host)

        logger.success(f"All stages in {self.__class__.__name__} are ready and started")


    def start(self, host):
        """Start processing thread"""
        logger.info(f'Starting {self}')
        self._host = host
        self.on_start()

    def on_connect(self):
        # Implementable
        pass

    def on_disconnect(self):
        # Implementable
        pass