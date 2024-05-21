from abc import ABCMeta, abstractmethod

class BotPersona(metaclass=ABCMeta):
    @property
    @abstractmethod
    def prompt(self):
        pass

    @property
    @abstractmethod
    def context_chain(self):
        pass

    @property
    @abstractmethod
    def respond_chain(self):
        pass

    @property
    @abstractmethod
    def postprocess_chain(self):
        pass

    @abstractmethod
    def construct_input(self, user_msg, chat_history):
        pass
