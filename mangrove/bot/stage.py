from typing import Iterator, Optional, List, Dict
from itertools import chain
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage

from core.utils import logger
from core.stage import TextToTextStage
from core.data.text_packet import TextPacket
from .persona.protector_of_mangrove import ProtectorOfMangrove
from .persona.protector_of_mangrove_nemotron import ProtectorOfMangroveNemotron

class BotStage(TextToTextStage):
    
    def __init__(self, name: str, endpoint: str='openai', endpoint_kwargs: Dict={}, persona_kwargs: Dict={}, verbose: bool=False):
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
            self._persona = ProtectorOfMangrove(**persona_kwargs)
            from .endpoints.chat_openai import ChatOpenAIEndpoint
            self._endpoint = ChatOpenAIEndpoint(**endpoint_kwargs)
        elif endpoint == 'ollama':
            self._persona = ProtectorOfMangroveNemotron()
            from .endpoints.chat_ollama import ChatOllamaEndpoint
            self._endpoint = ChatOllamaEndpoint(**endpoint_kwargs)
        else:
            raise Exception(f"Unknown Endpoint {endpoint}, available endpoints: openai, ollama")
        
        self._endpoint.setup(self._persona)

        self._chat_history: List[BaseMessage] = []
        self._in_progress_human_message: Optional[HumanMessage] = None

        self._output_text_packet_generator: Iterator[TextPacket] = None
        self._partial_command = ""
        self._in_command = False

    def process(self, in_text_packet: TextPacket) -> None:
        assert isinstance(in_text_packet, TextPacket), f"Expected TextPacket, got {type(in_text_packet)}"
        logger.success(f"Processing: {in_text_packet}")
        
        # if the input is empty, just return an empty generator
        if self._output_text_packet_generator is None:
            self._output_text_packet_generator = self.respond(in_text_packet)

        else:
            # interrupt the current conversation and replace with new input
            # self.schedule_forward_interrupt() # TODO review the interrupt logic
            logger.warning('Interrupting current conversation with new input')
            self._output_text_packet_generator = None
            # if chat history has ended with an AIMessage, delete it
            if len(self._chat_history) > 0 and isinstance(self._chat_history[-1], AIMessage):
                self._chat_history.pop()
            
            if self._in_progress_human_message is not None:
                logger.warning(f'Interrupting current conversation with in-progress human message: {self._in_progress_human_message}')
                # self._chat_history.append(self._in_progress_human_message)
                # TODO just old input be attached to new input?

            self._output_text_packet_generator = self.respond(in_text_packet)
            logger.warning(f'Interrupting current conversation with new input: {in_text_packet}')

            # TODO remove the below code if not needed
            # assumption that it has already generating, ignore new input for now
            # logger.warning(f'Dropping new input, already generating: {in_text_packet}')     

        self.pack(self._output_text_packet_generator)
        logger.warning("PACKING OBJECT OF TYPE: " + str(type(self._output_text_packet_generator)))

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