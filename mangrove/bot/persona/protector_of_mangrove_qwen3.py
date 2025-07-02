import json
from typing import Dict
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import format_document, ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, Runnable
from langchain_core.prompts.prompt import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from operator import itemgetter
from .base import BotPersona
from .protector_of_mangrove import *

class ProtectorOfMangroveQwen3(ProtectorOfMangrove):
    def __init__(self, persona_file: str=None):
        # Load persona data from JSON file
        if persona_file:
            with open(persona_file, 'r') as f:
                self.persona = json.load(f)
            self.assistant_name = self.persona.get("name")

        # Create dynamic system prompt using JSON fields
        system_prompt = self._create_system_prompt()
        
        self._prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate.from_template(
                    template=[
                        {"type": "text", "text": system_prompt},
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
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", "!", "?"], 
            chunk_size=200, 
            chunk_overlap=0
        )
        self.KNOWLEDGE_BASE =  [chunk.strip() for chunk in splitter.split_text(self.persona.get("background"))]
        print(f"Knowledge base: {self.KNOWLEDGE_BASE}")
        self.vectorstore = FAISS.from_texts(self.KNOWLEDGE_BASE, embedding=OllamaEmbeddings(model="qwen3:8b"))

    def _create_system_prompt(self) -> str:
        """Create a dynamic system prompt using the JSON persona fields"""
        
        # Base template with placeholders for JSON fields
        base_template = """You are {name}, {tagline}

        {personality}

        {description}

        You have three actions available: [Follow User], [Sit Down], [Stop Following User].  

        When you want to perform one of these actions, you must produce it on a line by itself, enclosed in square brackets, like this: [Follow User]  

        If no action is needed, do not produce any bracketed text.  Limit your entire response to at most three sentences.

        Reply to the following given the following knowledge base (Be relatively concise):
        {context}
        """
        
        # Extract fields from persona JSON, with fallbacks
        name = self.persona.get("name", "an AI assistant")
        tagline = self.persona.get("tagline", "")
        personality = self.persona.get("personality", "You are helpful and friendly.")
        description = self.persona.get("description", "")
        
        # Format the template with the JSON data
        return base_template.format(
            name=name,
            tagline=tagline,
            personality=personality,
            description=description,
            context="{context}"  # Keep this as a placeholder for the context chain
        )