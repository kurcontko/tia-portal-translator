import logging
import os
from typing import Any, Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

from tia_portal_translator.services.base import TranslationError, TranslationService

logger = logging.getLogger(__name__)


class OpenAITranslationService(TranslationService):
    """Modern OpenAI translation service using the latest API with tenacity retry logic."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        source_language: str = "auto",
        target_language: str = "en",
        cache=None,
        max_concurrent_requests: int = 10,
        request_delay: float = 0.1,
        max_retries: int = 3,
        client: Optional[Any] = None,
        model: Optional[str] = None,
    ) -> None:
        """
        Initialize OpenAI translation service.
        
        Args:
            api_key: OpenAI API key (overrides OPENAI_API_KEY env var)
            source_language: Source language code
            target_language: Target language code
            cache: Translation cache instance
            max_concurrent_requests: Max concurrent API requests
            request_delay: Delay between requests in seconds
            max_retries: Maximum retry attempts for failed requests
            client: Optional AsyncOpenAI client for dependency injection (for testing)
            model: Optional model name (overrides OPENAI_MODEL env var)
        """
        super().__init__(
            api_key,
            source_language,
            target_language,
            cache,
            max_concurrent_requests=max_concurrent_requests,
            request_delay=request_delay,
            max_retries=max_retries,
        )
        
        if client is not None:
            # Use injected client (useful for testing)
            self.client = client
        else:
            # Create default client
            import openai

            self.client = openai.AsyncOpenAI(
                api_key=api_key or os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_API_BASE"),
            )
        
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def _create_completion(self, text: str):
        """Create completion with tenacity retry logic."""
        return await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional translator. "
                        f"Translate the following text to {self.target_language}. "
                        "Preserve formatting, line breaks, and technical terminology. "
                        "Return only the translation without explanations."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )

    async def translate(self, text: str) -> str:
        """Translate text using OpenAI's chat completion API."""
        try:
            response = await self._create_completion(text)
            content = response.choices[0].message.content
            if not content:
                raise TranslationError("OpenAI translation returned an empty response.")
            return content.strip()
        except TranslationError as exc:
            logger.error("OpenAI translation error: %s", exc)
            raise
        except Exception as exc:
            logger.error("OpenAI translation error: %s", exc)
            raise TranslationError(f"OpenAI translation failed: {exc}") from exc
