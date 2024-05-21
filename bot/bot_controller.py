from typing import Generator, Dict
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from .persona.protector_of_mangrove import ProtectorOfMangrove

class BotController:
    def __init__(self, assistant_name='Marvin'):
        self.persona = ProtectorOfMangrove(assistant_name=assistant_name)
        self.conversational_qa_chain = self.persona.respond_chain | ChatOpenAI(
            model="gpt-3.5-turbo",
        ) | StrOutputParser() | self.persona.postprocess_chain
        self.chat_history = []

    def respond(self, user_msg) -> Generator[Dict, None, None]:
        def format_response(content, partial=False):
            # format response from openai chat to be sent to the user
            formatted_response = {
                "text": [content],
                "commands": [],
                "partial": partial
            }
            return formatted_response


        chat_history_formated = ""
        for llm_res in self.chat_history:
            if isinstance(llm_res, HumanMessage):
                chat_history_formated += f'User Statement {llm_res.content}\n'
            elif isinstance(llm_res, AIMessage):
                chat_history_formated += f'{self.assistant_name} {llm_res.content}\n'
            else:
                raise Exception(f'{llm_res} is not supported nor expected!')

        ai_content = self.conversational_qa_chain.invoke(
            self.persona.construct_input(user_msg, chat_history_formated)
        )
        self.chat_history.append(HumanMessage(content=user_msg))
        self.chat_history.append(AIMessage(content=ai_content))

        yield format_response(self.chat_history[-1].content, partial=False)

        # ai_msg_stream = self.conversational_qa_chain.stream(
        #     {
        #         "user_msg": user_msg,
        #         "chat_history": [],
        #     }
        # )
        # self.chat_history.append(HumanMessage(content=user_msg))
        # response_msg = ""
        # for chunk in ai_msg_stream:
        #     response_msg += chunk.content
        #     if chunk.content == "":
        #         continue
        #     yield self.format_response(chunk.content, partial=True)

        # yield self.format_response(response_msg)

        # self.chat_history.append(AIMessage(content=response_msg))


    def process_procedures_if_on(self):
        # TODO: Implement
        pass
