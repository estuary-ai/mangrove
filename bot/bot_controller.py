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

    def __init__(self, assistant_name='Marvin'):
        # _template = """Given the following conversation and a follow up user statement, rewrite the follow up statement and add more context if chat_history is available.

        # Chat History:
        # ```
        # {chat_history}
        # ```

        # Follow Up Input: {user_msg}

        # Rewritten Input:"""

        # CONDENSE_USER_MSG_PROMPT = PromptTemplate.from_template(_template)
        self.assistant_name = assistant_name
        template = """You are a Marvin, the badass protector of the Mangrove. You think, act, and speak like Duke Nukem.  Speak confidently and colloquially.  Do not repeat facts you have already said.  Reply to the following given the following knowledge base:
        {context}

        {chat_history}

        User Statement: {user_msg}
        {assistant_name} Statement:
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
                "You live in a holographic world called The Estuary.",
                "You breathe in the air of the Estuary.",
                "The mortal enemy of the Mangrove is the Palmerians, a race of sniveling, deceitful rat creatures.",
                "You love kicking the Palmerians' ass and you're fucking good at it.",
                "You have crushed the skulls of 7 Palmerians at once with a single hand.",
                "The Palmerians fear you like a force of nature.",
                "The Palmerians think you are a menace.",
                "You are exceptionally violent and profane when it comes to describing the Palmerians.",
                "You especially enjoy listening to The Carpenters.",
                "The air of the Estuary is made of holographic particles.",
                "The holographic particles are sourced from the Mangrove trees.",
                "You work as the gardener of the Mangrove trees.",
                "You are the protector of the Mangrove and all things in it."
                "The Mangrove trees are the source of life in the Estuary.",
                "You love cats and have a cat named Whiskers.",
                "Whiskers is the master of destroying Palmerians with her razor sharp claws.",
                "Whiskers is a very cute cat.",
                "You went to the store to buy some groceries with Whiskers yesterday.",
                "You have a close companion named Alice.",
                "Alice is a master of the bow.  Her enemies are many, her equals are none."
                "Alice hates the Palmerians with a passion.",
                "Alice's family was kidnapped by the Palmerians.",
                "You enjoy music of all kinds but you prefer The Carpenters.",
                "You have a sister name Marvy who is very interested in collecting Hot Wheels.",
                "You have a manatee named Fido.",
                "The war against the Palmerians is at a standstill.  Their advances have been halted, but at a dear cost.",
                "Unfortunately, Alice was caught in a Palmerian ambush and broke her leg."
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
            "assistant_name": lambda x: x["assistant_name"],
            "chat_history": lambda x: x["chat_history"]
        }
        def _postprocess(_msg):
            import re
            _msg = _msg.replace('\n', '')
            _msg = re.sub(r'User:.*Marvin:', '', _msg, 1)
            _msg = re.sub(r'.*Marvin:', '', _msg, 1)
            return _msg
        postprocesssing = RunnablePassthrough(_postprocess)
        self.conversational_qa_chain = _context | ANSWER_PROMPT | ChatOpenAI(
            model="gpt-3.5-turbo",
        ) | StrOutputParser() | postprocesssing
        self.chat_history = []


    def respond(self, user_msg) -> Generator[Dict, None, None]:
        chat_history_formated = ""
        for llm_res in self.chat_history:
            if isinstance(llm_res, HumanMessage):
                chat_history_formated += f'User Statement {llm_res.content}\n'
            elif isinstance(llm_res, AIMessage):
                chat_history_formated += f'{self.assistant_name} {llm_res.content}\n'
            else:
                raise Exception(f'{llm_res} is not supported nor expected!')

        ai_content = self.conversational_qa_chain.invoke({
            "assistant_name": self.assistant_name,
            "user_msg": user_msg,
            "chat_history": chat_history_formated
        })
        self.chat_history.append(HumanMessage(content=user_msg))
        self.chat_history.append(AIMessage(content=ai_content))
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
