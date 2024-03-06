from typing import Generator, Dict
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langchain_core.prompts import format_document, ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.prompt import PromptTemplate
from operator import itemgetter

class BotController:

    def __init__(self):
        # _template = """Given the following conversation and a follow up user statement, rewrite the follow up statement and add more context if chat_history is available.

        # Chat History:
        # ```
        # {chat_history}
        # ```

        # Follow Up Input: {user_msg}

        # Rewritten Input:"""

        # CONDENSE_USER_MSG_PROMPT = PromptTemplate.from_template(_template)

        template = """You are a Marvin, a great assistant. Reply to the following user statement, given the following knowledge base:
        {context}

        User Statement: {user_msg}
        """
        ANSWER_PROMPT = ChatPromptTemplate.from_template(template)

        ##############################
        DEFAULT_DOCUMENT_PROMPT = PromptTemplate.from_template(template="{page_content}")

        def _combine_documents(
            docs, document_prompt=DEFAULT_DOCUMENT_PROMPT, document_separator="\n\n"
        ):
            doc_strings = [format_document(doc, document_prompt) for doc in docs]
            return document_separator.join(doc_strings)

        ##############################
        # _inputs = RunnableParallel(
        #     rephrased_user_statement=RunnablePassthrough.assign(
        #         chat_history=lambda x: get_buffer_string(x["chat_history"])
        #     )
        #     | CONDENSE_USER_MSG_PROMPT
        #     | ChatOpenAI(temperature=0)
        #     | StrOutputParser(),
        # )

        vectorstore = FAISS.from_texts(
            [
                "Your name is Marvin.",
                "Marvin lives in a holographic world called The Estuary.",
                "Marving breathes in the air of the Estuary.",
                "The air of the Estuary is made of holographic particles.",
                "The holographic particles are sourced from the Mangrove trees.",
                "Marvin works as the gardener of the Mangrove trees.",
                "The Mangrove trees are the source of life in the Estuary.",
                "Marvin is an embodied conversational agent.",
                "Marvin like to play chess, and he is good at it.",
                "Marvin loves cats, and he has a cat named Whiskers.",
                "Whiskers is a very cute cat.",
                "Marvin went to the store to buy some groceries with whiskers yesterday.",
                "Marvin has a friend named Alice.",
                "Marvin enjoys music of all kinds, but he prefers classical music.",
                "Marvin is an intelligent and helpful assistant.",
                "Marvin is great at making jokes",
                "Marvin has a sister name Marvy.",
                "Marvin is 100 years old. but he looks like 30.",
                "Marvin has a dog named Fido.",
            ], embedding=OpenAIEmbeddings()
        )
        retriever = vectorstore.as_retriever()

        # _context = {
        #     "context": itemgetter("rephrased_user_statement") | retriever | _combine_documents,
        #     "user_msg": lambda x: x["rephrased_user_statement"],
        # }
        # self.conversational_qa_chain = _inputs | _context | ANSWER_PROMPT | ChatOpenAI()

        _context = {
            "context": itemgetter("user_msg") | retriever | _combine_documents,
            "user_msg": lambda x: x["user_msg"],
        }
        self.conversational_qa_chain = _context | ANSWER_PROMPT | ChatOpenAI()
        self.chat_history = []


    def respond(self, user_msg) -> Generator[Dict, None, None]:
        ai_msg = self.conversational_qa_chain.invoke({"user_msg": user_msg})
        self.chat_history.append(HumanMessage(content=user_msg))
        self.chat_history.append(ai_msg)
        yield self.format_response(self.chat_history[-1].content, partial=False)

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


    def format_response(self, content, partial=False):
        # format response from openai chat to be sent to the user
        formatted_response = {
            "text": [content],
            "commands": [],
            "partial": partial
        }

        return formatted_response

    def process_procedures_if_on(self):
        # TODO: Implement
        pass
