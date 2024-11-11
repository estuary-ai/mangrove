from langchain_ollama import ChatOllama

from .base import LangchainCompatibleConversationalChainEndpoint

class ChatOllamaEndpoint(LangchainCompatibleConversationalChainEndpoint):
    def __init__(
        self,
        model='nemotron-mini',
        temperature = 0.8,
        num_predict = 256,
        **llm_kwargs
    ):
        self._llm = ChatOllama(
            model=model,
            temperature=temperature,
            num_predict=num_predict,
            **llm_kwargs
        )

    @property   
    def llm(self):
        return self._llm
                    
