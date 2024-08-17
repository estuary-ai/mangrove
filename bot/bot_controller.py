from typing import Generator, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from core.stage import TextToTextStage
from bot.persona.protector_of_mangrove import ProtectorOfMangrove
from core.data.text_packet import TextPacket
from itertools import chain

class BotController(TextToTextStage):
    def __init__(self, assistant_name='Marvin', verbose=False):
        super().__init__(verbose=verbose)
        self._persona = ProtectorOfMangrove(assistant_name=assistant_name)

        # TODO create other endpoints
        self._conversational_qa_chain = self._persona.respond_chain | ChatOpenAI(
            model="gpt-3.5-turbo",
        ) | StrOutputParser() | self._persona.postprocess_chain
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
            ai_msg_stream = self._conversational_qa_chain.stream(
                self._persona.construct_input(user_msg, chat_history_formated)
            )
            ai_res_content = ""
            first_chunk = True
            for chunk in ai_msg_stream:
                ai_res_content += chunk
                if chunk == "":
                    continue
                # TODO append to ai message internally
                yield _pack_response(chunk, partial=True, start=first_chunk)
                first_chunk = False
            yield _pack_response(ai_res_content)
            self._chat_history.append(AIMessage(content=ai_res_content))

    def process_procedures_if_on(self):
        # TODO: Implement in different stage
        pass
