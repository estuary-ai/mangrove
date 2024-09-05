from abc import ABCMeta, abstractmethod
from typing import Iterator
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

from ..persona.base import BotPersona

class NotSetupYetError(Exception):
    pass

class ConversationalChainEndpoint(metaclass=ABCMeta):
    pass

class LangchainCompatibleConversationalChainEndpoint(ConversationalChainEndpoint):

    @property
    @abstractmethod
    def llm(self) -> Runnable:
        raise NotImplementedError("You must implement the llm property in your subclass")

    def setup(self, persona: BotPersona):
        self._persona = persona
        self._chain: Runnable = (
            persona.respond_chain 
            | self.llm 
            | StrOutputParser() 
            | persona.postprocess_chain
        )

    @property
    def persona(self) -> BotPersona:
        if not hasattr(self, '_persona'):
            raise NotSetupYetError("You must call setup() before accessing the persona")
        return self._persona

    @property
    def chain(self) -> Runnable:
        if not hasattr(self, '_chain'):
            raise NotSetupYetError("You must call setup() before accessing the chain")
        return self._chain
    
    def stream(self, user_msg, chat_history_formated) -> Iterator[str]:
        return self._chain.stream(
            self._persona.construct_input(user_msg, chat_history_formated)
        )