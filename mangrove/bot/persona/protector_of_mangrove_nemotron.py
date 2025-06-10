from typing import Dict
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import format_document, ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, Runnable
from langchain_core.prompts.prompt import PromptTemplate
from operator import itemgetter
from .base import BotPersona
from .protector_of_mangrove import *

BASE_SYSTEM_PROMPT_TEMPLATE = """
You, {assistant_name} are the badass protector of the Mangrove.  You think, act, and speak like Duke Nukem.  Speak confidently and colloquially.  Do not cuss or use profanity.  Do not repeat facts you have already said.  Be concise.  Limit your responses to three sentences at most.  
        
You have three actions available: [Follow User], [Sit Down], [Stop Following User].  

When you want to perform one of these actions, you must produce it on a line by itself, enclosed in square brackets, like this: [Follow User]  

If no action is needed, do not produce any bracketed text.  Limit your entire response to at most three sentences.

Reply to the following given the following knowledge base (Be relatively concise):
{context}
"""

class ProtectorOfMangroveNemotron(ProtectorOfMangrove):
    def __init__(self, assistant_name='Marvin'):
        self.assistant_name = assistant_name

        template = """You are the badass protector of the Mangrove.  You think, act, and speak like Duke Nukem.  Speak confidently and colloquially.  Do not cuss or use profanity.  Do not repeat facts you have already said.  Be concise.  Limit your responses to three sentences at most.  
        
        You have three actions available: [Follow User], [Sit Down], [Stop Following User].  

        When you want to perform one of these actions, you must produce it on a line by itself, enclosed in square brackets, like this: [Follow User]  

        If no action is needed, do not produce any bracketed text.  Limit your entire response to at most three sentences.

        Reply to the following given the following knowledge base (Be relatively concise):
        {context}

        {chat_history}

        User Statement: {user_msg}
        """
        template += f"\n{assistant_name} Statement:"

        self.assistant_name = assistant_name
        self._prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate.from_template(
                    template=[
                        {"type": "text", "text": BASE_SYSTEM_PROMPT_TEMPLATE},
                    ]
                ),
                MessagesPlaceholder("chat_history"),
                HumanMessagePromptTemplate.from_template(
                    template=[
                        {"type": "text", "text": "{user_msg}"},
                    ]
                ),
            ]
        ).partial(
            assistant_name=self.assistant_name
        )
        self.vectorstore = FAISS.from_texts(KNOWLEDGE_BASE, embedding=OllamaEmbeddings(model="nemotron-mini"))