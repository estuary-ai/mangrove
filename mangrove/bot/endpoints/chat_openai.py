from langchain_openai import ChatOpenAI

from .base import LangchainCompatibleConversationalChainEndpoint

class ChatOpenAIEndpoint(LangchainCompatibleConversationalChainEndpoint):
    def __init__(self, **llm_kwargs):
        self._llm = ChatOpenAI(model="gpt-4o", **llm_kwargs)

    @property
    def llm(self):
        return self._llm