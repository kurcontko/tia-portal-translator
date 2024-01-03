from abc import ABC, abstractmethod


class TranslationService(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def translate(self, text, destination_language, source_language=None):
        raise NotImplementedError

    @abstractmethod
    def translate_batch(self, texts, destination_language, source_language=None):
        raise NotImplementedError