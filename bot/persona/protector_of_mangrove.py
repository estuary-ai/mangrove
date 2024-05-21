from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import format_document, ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts.prompt import PromptTemplate
from operator import itemgetter
from .base import BotPersona

class ProtectorOfMangrove(BotPersona):
    def __init__(self, assistant_name='Marvin'):
        self.assistant_name = assistant_name

        template = """You are the badass protector of the Mangrove. You think, act, and speak like Duke Nukem.  Speak confidently and colloquially.  Do not repeat facts you have already said.  Reply to the following given the following knowledge base:
        {context}

        {chat_history}

        User Statement: {user_msg}
        """
        template += f"\n{assistant_name} Statement:"

        self._prompt = ChatPromptTemplate.from_template(template)

        kb = [
            f"Your name is {assistant_name}.",
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
        ]
        self.vectorstore = FAISS.from_texts(kb, embedding=OpenAIEmbeddings())

    @property
    def prompt(self):
        return self._prompt

    @property
    def context_chain(self):
        def _combine_documents(
            docs, document_separator="\n\n"
        ):
            document_prompt = PromptTemplate.from_template(template="{page_content}")
            doc_strings = [format_document(doc, document_prompt) for doc in docs]
            return document_separator.join(doc_strings)

        retriever = self.vectorstore.as_retriever()
        return {
            "context": itemgetter("user_msg") | retriever | _combine_documents,
            "user_msg": lambda x: x["user_msg"],
            "chat_history": lambda x: x["chat_history"]
        }

    @property
    def respond_chain(self):
        return self.context_chain | self.prompt

    @property
    def postprocess_chain(self):
        def _postprocess(_msg):
            import re
            _msg = _msg.replace('\n', '')
            _msg = re.sub(rf'User:.*{self.assistant_name}:', '', _msg, 1)
            _msg = re.sub(rf'.*{self.assistant_name}:', '', _msg, 1)
            return _msg

        return RunnablePassthrough(_postprocess)


    def construct_input(self, user_msg, chat_history):
        return {
            "user_msg": user_msg,
            "chat_history": chat_history,
        }

