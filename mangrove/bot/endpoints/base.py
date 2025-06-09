from abc import ABCMeta, abstractmethod
from typing import Iterator, List
from copy import copy
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

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
    
    def stream(self, user_msg, chat_history: List[BaseMessage]) -> Iterator[str]:     
        # chat_history_formatted: str = ""
        # for message in chat_history:
        #     if isinstance(message, HumanMessage):
        #         chat_history_formatted += f'User Statement: {message.content}\n'
        #     elif isinstance(message, AIMessage):
        #         chat_history_formatted += f'{self._persona.assistant_name} Statement: {message.content}\n'
        #     else:
        #         raise Exception(f'{message} is not of expected type!')
               
        return self._chain.stream(
            self._persona.construct_input(user_msg, chat_history)
        )