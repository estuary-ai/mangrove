from abc import ABCMeta, abstractmethod
from typing import Dict
from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate

class BotPersona(metaclass=ABCMeta):
    @property
    @abstractmethod
    def prompt(self) -> ChatPromptTemplate:
        pass

    @property
    @abstractmethod
    def context_chain(self) -> Runnable:
        pass

    @property
    @abstractmethod
    def respond_chain(self) -> Runnable:
        pass

    @property
    @abstractmethod
    def postprocess_chain(self) -> Runnable:
        pass

    @abstractmethod
    def construct_input(self, user_msg, chat_history) -> Dict:
        pass
