from typing import List, Dict
from abc import ABC, abstractmethod


class TokenCounter(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def count(self, text: str) -> int:
        raise NotImplementedError
    
    @abstractmethod
    def count_multiple(self, texts: List[str]) -> List[int]:
        raise NotImplementedError
