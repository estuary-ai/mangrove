from threading import Lock
from typing import Generator, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from multiprocessing import JoinableQueue
from queue import Empty
from loguru import logger
from bot.persona.protector_of_mangrove import ProtectorOfMangrove

class BotController:
    def __init__(self, assistant_name='Marvin'):
        self.persona = ProtectorOfMangrove(assistant_name=assistant_name)
        self.conversational_qa_chain = self.persona.respond_chain | ChatOpenAI(
            model="gpt-3.5-turbo",
        ) | StrOutputParser() | self.persona.postprocess_chain
        self.chat_history = []
        self._lock = Lock()

        self._input_queue = JoinableQueue()
        self._output_buffer = JoinableQueue()

    def start(self, server):
        def _start_thread():
            while True:
                texts = []
                try:
                    while True:
                        texts.append(self._input_queue.get_nowait())
                except Empty:
                    pass

                text = " ".join(texts)

                if not text:
                    server.sleep(0.05)
                    # print('<bot>', end='', flush=True)
                else:
                    bot_res_generator = self.respond(text)
                    while True:
                        partial_bot_res = next(bot_res_generator, None)
                        if partial_bot_res is None:
                            break
                        self._output_buffer.put(partial_bot_res)

        self._process = server.start_background_task(_start_thread)

    def feed(self, text):
        self._input_queue.put(text)

    def receive(self):
        try:
            return self._output_buffer.get_nowait()
        except Empty:
            return None

    def respond(self, user_msg) -> Generator[Dict, None, None]:
        def _format_response(content, partial=False, start=False):
            # format response from openai chat to be sent to the user
            formatted_response = {
                "text": content,
                "commands": [],
                "partial": partial,
                "start": start,
            }
            return formatted_response

        with self._lock:
            chat_history_formated = ""
            for llm_res in self.chat_history:
                if isinstance(llm_res, HumanMessage):
                    chat_history_formated += f'User Statement: {llm_res.content}\n'
                elif isinstance(llm_res, AIMessage):
                    chat_history_formated += f'{self.persona.assistant_name} Statement: {llm_res.content}\n'
                else:
                    raise Exception(f'{llm_res} is not supported nor expected!')

            self.chat_history.append(HumanMessage(content=user_msg))
            ai_msg_stream = self.conversational_qa_chain.stream(
                self.persona.construct_input(user_msg, chat_history_formated)
            )
            ai_res_content = ""
            first_chunk = True
            for chunk in ai_msg_stream:
                ai_res_content += chunk
                if chunk == "":
                    continue
                # TODO append to ai message internally
                yield _format_response(chunk, partial=True, start=first_chunk)
                first_chunk = False
            yield _format_response(ai_res_content)
            self.chat_history.append(AIMessage(content=ai_res_content))

    def process_procedures_if_on(self):
        # TODO: Implement
        pass
