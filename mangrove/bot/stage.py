from typing import Iterator, Optional, List, Dict
from itertools import chain
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from threading import Lock

from core.utils import logger
from core.stage import TextToTextStage
from core.data.text_packet import TextPacket
from .persona.protector_of_mangrove import ProtectorOfMangrove
from .persona.protector_of_mangrove_nemotron import ProtectorOfMangroveNemotron
from .persona.protector_of_mangrove_qwen3 import ProtectorOfMangroveQwen3

class BotStage(TextToTextStage):
    def __init__(self, name: str, endpoint: str='openai', persona_configs: Union[Dict[str, str], str]={},  endpoint_kwargs: Dict={}, verbose: bool=False):
        """Initialize Bot Stage

        Args:
            name (str): Name of the stage.
            endpoint (str, optional): Endpoint to use for the bot. Defaults to 'openai'.
            endpoint_kwargs (Dict, optional): Additional keyword arguments for the endpoint. Defaults to {}.
            persona_kwargs (Dict, optional): Additional keyword arguments for the persona. Defaults to {}.
            verbose (bool, optional): Whether to print debug messages. Defaults to False.
        """
        super().__init__(name=name, verbose=verbose)
        
        if endpoint == 'openai':
            from .persona.protector_of_mangrove import ProtectorOfMangrove
            persona_kwargs = persona_configs if isinstance(persona_configs, dict) else {}
            self._persona = ProtectorOfMangrove(**persona_kwargs)
            from .endpoints.chat_openai import ChatOpenAIEndpoint
            self._endpoint = ChatOpenAIEndpoint(**endpoint_kwargs)
        elif endpoint == 'ollama':
            from .persona.protector_of_mangrove_qwen3 import ProtectorOfMangroveQwen3
            self._persona = ProtectorOfMangroveQwen3(persona_file=persona_configs)
            from .endpoints.chat_ollama import ChatOllamaEndpoint
            self._endpoint = ChatOllamaEndpoint(**endpoint_kwargs)
        else:
            raise Exception(f"Unknown Endpoint {endpoint}, available endpoints: openai, ollama")
        
        self._endpoint.setup(self._persona)

        self._chat_history: List[BaseMessage] = []
        self._in_progress_user_text_packet: Optional[TextPacket] = None

        self._partial_command = ""
        self._in_command = False
        self._is_supplementary_input_in_progress: bool = False
        self._responding_lock = Lock()

    def process(self, in_text_packet: TextPacket) -> None:
        assert isinstance(in_text_packet, TextPacket), f"Expected TextPacket, got {type(in_text_packet)}"
        logger.success(f"Processing incoming: {in_text_packet}")

        # if there is incoming packet; we should invalidate in-progress outcoming packets if any
        if self._in_progress_user_text_packet:
            # make use of the in-progress user text packet
            logger.warning(f"Supplementary input is in progress, appending to in-progress user text packet: {self._in_progress_user_text_packet}")
            from core.context import Context
            Context().record_invalidating_timestamp(in_text_packet)
            new_timestamp = in_text_packet.timestamp
            in_text_packet = self._in_progress_user_text_packet + in_text_packet
            in_text_packet._timestamp = new_timestamp  # keep the timestamp of the new input
            self._in_progress_user_text_packet = None
            logger.success(f"New input: {in_text_packet}")

        _output_text_packet_generator: Iterator[TextPacket] = self.respond(in_text_packet)

        # if the input is empty, just return an empty generator
        # if self._output_text_packet_generator is None:
        #     self._output_text_packet_generator = self.respond(in_text_packet)

        # else:
        #     # interrupt the current conversation and replace with new input
        #     # self.schedule_forward_interrupt() # TODO review the interrupt logic
        #     logger.warning('Interrupting current conversation with new input')
        #     self._output_text_packet_generator = None
        #     # if chat history has ended with an AIMessage, delete it
        #     if len(self._chat_history) > 0 and isinstance(self._chat_history[-1], AIMessage):
        #         self._chat_history.pop()
            
        #     if self._in_progress_user_text_packet is not None:
        #         logger.warning(f'Interrupting current conversation with in-progress human text packet: {self._in_progress_user_text_packet}')
        #         # self._chat_history.append(self._in_progress_user_text_packet)
        #         # TODO just old input be attached to new input?

        #     self._output_text_packet_generator = self.respond(in_text_packet)
        #     logger.warning(f'Interrupting current conversation with new input: {in_text_packet}')

        #     # TODO remove the below code if not needed
        #     # assumption that it has already generating, ignore new input for now
        #     # logger.warning(f'Dropping new input, already generating: {in_text_packet}')     

        self.pack(_output_text_packet_generator)

    # refactor it as local scope method
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

    def respond(self, text_packet: TextPacket) -> Iterator[TextPacket]:
        def _pack_response(content, commands=[], partial=False, start=False):
            # format response from openai chat to be sent to the user
            return TextPacket(
                text=content,
                commands=commands,
                partial=partial,
                start=start
            )

        from core.context import OutcomingStreamContext, InvalidatingTimestampsException

        with self._responding_lock:
            try:
                with OutcomingStreamContext(text_packet, source=self) as stream_context:
                    self._in_progress_user_text_packet = text_packet.copy()
                    ai_res_content = ""
                    clean_ai_res_content = ""
                    current_commands = []
                    first_chunk = True
                    for chunk in self._endpoint.stream(
                        chat_history=self._chat_history,
                        user_msg=text_packet.text,
                    ):
                        stream_context.raise_error_if_any()
                        ai_res_content += chunk
                        if chunk == "":
                            continue

                        clean_text, commands = self._process_stream_chunk(chunk)
                        clean_ai_res_content += clean_text
                        current_commands += commands
                        yield _pack_response(clean_text, commands=commands, partial=True, start=first_chunk)
                        first_chunk = False
                    logger.success(f"Finished streaming AI response: {clean_ai_res_content}")
            except InvalidatingTimestampsException as e:  
                # return nothing and stop the generator if supplementary input is in progress
                assert text_packet.timestamp < e.timestamp, f"Invalidating timestamp should be greater than or equal to the text packet timestamp {text_packet.timestamp}, got {e.timestamp}"
                logger.warning(f"Invalid packet timestamp {text_packet.timestamp} is less than or equal invalidating timestamp {e.timestamp}, stopping response generation for text packet: {text_packet}")
                # yield _pack_response("", partial=False, start=True)
                # do not reset the in-progress user text packet, since it will be used by the process method
                
                if ai_res_content != "":
                    logger.warning(f"Invalidating timestamp {e.timestamp} occurred while generating AI response: {ai_res_content}. The response will not be added to the chat history.")
                return
            
            yield _pack_response(clean_ai_res_content, commands=current_commands, partial=False, start=True)
            self._chat_history.append(HumanMessage(content=text_packet.text))
            self._in_progress_user_text_packet = None
            # append the AIMessage to the chat history
            self._chat_history.append(AIMessage(content=ai_res_content))
            logger.success(f"Finished generating AI Response: {ai_res_content}")

    def process_procedures_if_on(self):
        # TODO: Implement in different stage
        pass

    # def on_interrupt(self):
    #     super().on_interrupt()
    #     if self._output_text_packet_generator is not None:
    #         assert self._in_progress_user_text_packet is not None, \
    #             "In progress human text packet should not be None when interrupting"
    #         logger.warning(f'Interrupting conversation, dropping in progress human text packet: {self._in_progress_user_text_packet}')
    #         logger.warning('Interrupting conversation, dropping text packet generator')
    #         self._output_text_packet_generator = None
    #         # TODO adjust new input to include the in-progress human text packet as well as the new input
    #         self._in_progress_user_text_packet = None # TODO for now, just drop the in-progress human text packet
            
    #     # TODO review since that does not make sense apparently?
    #     # if len(self._chat_history) > 0 and isinstance(self._chat_history[-1], AIMessage):
    #     #     logger.warning('Interrupting conversation, removing last AIMessage')
    #     #     self._chat_history.pop()