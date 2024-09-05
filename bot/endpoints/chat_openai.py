from langchain_openai import ChatOpenAI

from .base import LangchainCompatibleConversationalChainEndpoint

class ChatOpenAIEndpoint(LangchainCompatibleConversationalChainEndpoint):
    def __init__(self, **llm_kwargs):
        self._llm = ChatOpenAI(**llm_kwargs)

    @property
    def llm(self):
        return self._llm