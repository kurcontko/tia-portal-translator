from typing import List
import tiktoken

from base import TokenCounter


class TikTokenCounter(TokenCounter):
    def __init__(self, model='gpt2'):
        self.tokenizer = tiktoken.encoding_for_model(model)

    def count(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def count_multiple(self, texts: List[str]) -> List[int]:
        return [self.count(text) for text in texts]