from typing import Generator, Optional, List, Dict
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage

from core.utils import logger
from core.stage import TextToTextStage
from core.data.text_packet import TextPacket
from core.stage.base import SequenceMismatchException, QueueEmpty
from .persona.protector_of_mangrove import ProtectorOfMangrove
from .persona.protector_of_mangrove_nemotron import ProtectorOfMangroveNemotron

class BotStage(TextToTextStage):
    
    def __init__(self, endpoint: str='openai', endpoint_kwargs: Dict={}, persona_kwargs: Dict={}, verbose: bool=False):
        """Initialize Bot Stage

        Args:
            endpoint (str, optional): Endpoint to use for the bot. Defaults to 'openai'.
            endpoint_kwargs (Dict, optional): Additional keyword arguments for the endpoint. Defaults to {}.
            persona_kwargs (Dict, optional): Additional keyword arguments for the persona. Defaults to {}.
            verbose (bool, optional): Whether to print debug messages. Defaults to False.
        """
        super().__init__(verbose=verbose)
        
        if endpoint == 'openai':
            self._persona = ProtectorOfMangrove(**persona_kwargs)
            from .endpoints.chat_openai import ChatOpenAIEndpoint
            self._endpoint = ChatOpenAIEndpoint(**endpoint_kwargs)
        # elif endpoint == 'ollama':
        #     self._persona = ProtectorOfMangroveNemotron()
        #     from .endpoints.chat_ollama import ChatOllamaEndpoint
        #     self._endpoint = ChatOllamaEndpoint(**endpoint_kwargs)
        else:
            raise Exception(f"Unknown Endpoint {endpoint}, available endpoints: openai, ollama")
        
        self._endpoint.setup(self._persona)

        self._chat_history: List[BaseMessage] = []
        self._in_progress_human_message: Optional[HumanMessage] = None

        self._output_text_packet_generator: Generator[TextPacket, None, None] = None
        self._partial_command = ""
        self._in_command = False

    def _process(self, in_text_packet: TextPacket) -> Optional[TextPacket]:
        assert isinstance(in_text_packet, TextPacket), f"Expected TextPacket, got {type(in_text_packet)}"
  
        logger.success(f"Processing: {in_text_packet}")

        return self.respond(in_text_packet)
    
        # else:
        #     # interrupt the current conversation and replace with new input
        #     self.schedule_forward_interrupt()
        #     self._output_text_packet_generator = None
        #     # if chat history has ended with an AIMessage, delete it
        #     if len(self._chat_history) > 0 and isinstance(self._chat_history[-1], AIMessage):
        #         self._chat_history.pop()
            
        #     if self._in_progress_human_message is not None:
        #         logger.warning(f'Interrupting current conversation with in-progress human message: {self._in_progress_human_message}')
        #         # self._chat_history.append(self._in_progress_human_message)
        #         # TODO just old input be attached to new input?

        #     self._output_text_packet_generator = self.respond(in_text_packet)
        #     logger.warning(f'Interrupting current conversation with new input: {in_text_packet}')

        #     # TODO remove the below code if not needed
        #     # assumption that it has already generating, ignore new input for now
        #     # logger.warning(f'Dropping new input, already generating: {in_text_packet}')            
        
        # # TODO pass down the generator to the next stage
        # # if self._output_text_packet_generator:
        # #     try:
        # #         out_text_packet = next(self._output_text_packet_generator)
        # #         return out_text_packet
        # #     except StopIteration:
        # #         self._output_text_packet_generator = None

        # return True
    
    def on_interrupt(self):
        super().on_interrupt()
        if self._output_text_packet_generator is not None:
            assert self._in_progress_human_message is not None, \
                "In progress human message should not be None when interrupting"
            logger.warning(f'Interrupting conversation, dropping in progress human message: {self._in_progress_human_message}')
            logger.warning('Interrupting conversation, dropping text packet generator')
            self._output_text_packet_generator = None
            # TODO adjust new input to include the in-progress human message as well as the new input
            self._in_progress_human_message = None # TODO for now, just drop the in-progress human message
            
        # TODO review since that does not make sense apparently?
        # if len(self._chat_history) > 0 and isinstance(self._chat_history[-1], AIMessage):
        #     logger.warning('Interrupting conversation, removing last AIMessage')
        #     self._chat_history.pop()

    def on_sleep(self) -> None:
        return self.log('<bot>')

    def _process_stream_chunk(self, chunk: str) -> tuple[str, list[str]]:
        clean_text = ""
        commands = []
        
        for char in chunk:
            if char == '[':
                self._in_command = True
                self._partial_command = '['
            elif char == ']' and self._in_command:
                self._in_command = False
                self._partial_command += ']'
                commands.append(self._partial_command[1:-1])
                self._partial_command = ""
            elif self._in_command:
                self._partial_command += char
            else:
                clean_text += char
        return clean_text, commands

    def respond(self, text_packet: TextPacket) -> Generator[TextPacket, None, None]:
        def _pack_response(content, commands=[], partial=False, start=False):
            # format response from openai chat to be sent to the user
            return TextPacket(
                text=content,
                commands=commands,
                partial=partial,
                start=start
            )

        self._in_progress_human_message = HumanMessage(content=text_packet.text)
        ai_res_content = ""
        clean_ai_res_content = ""
        current_commands = []
        first_chunk = True
        for chunk in self._endpoint.stream(
            chat_history=self._chat_history,
            user_msg=self._in_progress_human_message.content, 
        ):
            ai_res_content += chunk
            if chunk == "":
                continue

            clean_text, commands = self._process_stream_chunk(chunk)
            clean_ai_res_content += clean_text
            current_commands += commands
            yield _pack_response(clean_text, commands=commands, partial=True, start=first_chunk)
            first_chunk = False

        yield _pack_response(clean_ai_res_content, commands=current_commands, partial=False, start=True)
        self._chat_history.append(self._in_progress_human_message)
        self._in_progress_human_message = None
        # append the AIMessage to the chat history
        self._chat_history.append(AIMessage(content=ai_res_content))

    def process_procedures_if_on(self):
        # TODO: Implement in different stage
        pass


    def feed(self, data_packet: TextPacket) -> None:
        logger.debug(f"Feeding text packet {data_packet} to stage {self.__class__.__name__}")
        self._input_buffer.put(data_packet)
        logger.debug(f"Text packet {data_packet} fed to stage {self.__class__.__name__}")

    def _unpack(self) -> TextPacket:
        data_packets: List[TextPacket] = self._intermediate_input_buffer
        self._intermediate_input_buffer = []

        if not self._intermediate_input_buffer: # if intermediate buffer is empty, we need to get at least one packet from input buffer
            data_packet = self._input_buffer.get(timeout=None) # blocking call at least for the first time
            data_packets.append(data_packet)
        else:
            logger.debug("Intermediate buffer is not empty, skipping first get from input buffer")

        # Now we have at least one packet in data_packets, we can try to get more packets
        while True:
            try:
                data_packet = self._input_buffer.get_nowait()
                data_packets.append(data_packet)
            except QueueEmpty:
                # if len(data_packets) == 0:
                #     # logger.warning('No audio packets found in buffer', flush=True)
                #     return
                break

        complete_data_packet = data_packets[0]
        for i, data_packet in enumerate(data_packets[1:], start=1):
            try:
                complete_data_packet += data_packet
            except SequenceMismatchException as e:
                for j in range(i, len(data_packets)):
                    self._intermediate_input_buffer.append(data_packets[j])
                break
        
        return complete_data_packet

    def start(self, host):
        """Start processing thread"""
        logger.info(f'Starting {self}')

        self._host = host

        self.on_start()

        def _start_thread():
            while True:
                with self._lock:
                    logger.debug(f"Unpacking data in {self.__class__.__name__}")
                    data = self._unpack()
                    logger.debug(f"Unpacked data: {data}")
                    assert isinstance(data, TextPacket), f"Expected TextPacket, got {type(data)}"
                    data_packet = self._process(data)
                    logger.success(f"Processed data packet: {data_packet}")
                    
                    if self._is_interrupt_signal_pending:
                        logger.warning(f"Interrupt signal pending in {self.__class__.__name__}, calling on_interrupt")
                        self.on_interrupt()

                    logger.debug(f"Data packet after processing: {data_packet}")
                    if data_packet is not None and not isinstance(data_packet, bool):
                        # TODO this is just hacky way.. use proper standards
                        self.on_ready(data_packet)
                        logger.debug(f"Data packet {data_packet} sent to on_ready in {self.__class__.__name__}")
                    

        self._processor = self._host.start_background_task(_start_thread)
