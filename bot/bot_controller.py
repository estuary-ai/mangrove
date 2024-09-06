from typing import Generator, Optional, List
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from itertools import chain

from core.stage import TextToTextStage
from bot.persona.protector_of_mangrove import ProtectorOfMangrove
from core.data.text_packet import TextPacket

class BotController(TextToTextStage):
    def __init__(self, assistant_name='Marvin', verbose=False, endpoint='openai', endpoint_kwargs={}):
        super().__init__(verbose=verbose)
        self._persona = ProtectorOfMangrove(assistant_name=assistant_name)
        if endpoint == 'openai':
            from .endpoints.chat_openai import ChatOpenAIEndpoint
            self._endpoint = ChatOpenAIEndpoint(**endpoint_kwargs)
        elif endpoint == 'ollama':
            from .endpoints.chat_ollama import ChatOllamaEndpoint
            self._endpoint = ChatOllamaEndpoint(**endpoint_kwargs)
        else:
            raise Exception(f"Unknown Endpoint {endpoint}, available endpoints: openai, ollama")
        
        self._endpoint.setup(self._persona)

        self._chat_history: List[BaseMessage] = []
        self._text_packet_generator: Generator[TextPacket, None, None] = None


    def _process(self, in_text_packet: TextPacket) -> Optional[TextPacket]:
        if in_text_packet is None and self._text_packet_generator is None:
            return None

        if self._text_packet_generator:
            try:
                out_text_packet = next(self._text_packet_generator)
                return out_text_packet
            except StopIteration:
                self._text_packet_generator = None

        if in_text_packet:
            if self._text_packet_generator is None:
                self._text_packet_generator = self.respond(in_text_packet.text)
            else:
                # TODO: Implement Interruption Logic
                _new_text_packet_generator = self.respond(in_text_packet.text)
                self._text_packet_generator = chain(
                    self._text_packet_generator,
                    _new_text_packet_generator
                )
        return True

    def on_sleep(self) -> None:
        return self.log('<bot>')

    def respond(self, user_msg) -> Generator[TextPacket, None, None]:
        def _pack_response(content, partial=False, start=False):
            # format response from openai chat to be sent to the user
            return TextPacket(
                text=content,
                commands=[],
                partial=partial,
                start=start
            )

        with self._lock:
            chat_history_formated = ""
            for message in self._chat_history:
                if isinstance(message, HumanMessage):
                    chat_history_formated += f'User Statement: {message.content}\n'
                elif isinstance(message, AIMessage):
                    chat_history_formated += f'{self._persona.assistant_name} Statement: {message.content}\n'
                else:
                    raise Exception(f'{message} is not of expected type!')

            self._chat_history.append(HumanMessage(content=user_msg))
            
            ai_res_content = ""
            first_chunk = True
            for chunk in self._endpoint.stream(
                user_msg=user_msg, 
                chat_history_formated=chat_history_formated
            ):
                ai_res_content += chunk
                if chunk == "":
                    continue
                # TODO append to ai message internally
                yield _pack_response(chunk, partial=True, start=first_chunk)
                first_chunk = False
            yield _pack_response(ai_res_content, partial=False, start=True)
            self._chat_history.append(AIMessage(content=ai_res_content))

    def process_procedures_if_on(self):
        # TODO: Implement in different stage
        pass
