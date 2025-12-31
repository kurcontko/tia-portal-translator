import asyncio
import logging
import os
from typing import Optional

from tia_portal_translator.services.base import TranslationError, TranslationService

logger = logging.getLogger(__name__)


class DeepLTranslationService(TranslationService):
    """DeepL translation service with async support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        source_language: str = "auto",
        target_language: str = "EN",
        cache=None,
        max_concurrent_requests: int = 10,
        request_delay: float = 0.1,
        max_retries: int = 3,
    ) -> None:
        super().__init__(
            api_key,
            source_language,
            target_language.upper(),
            cache,
            max_concurrent_requests=max_concurrent_requests,
            request_delay=request_delay,
            max_retries=max_retries,
        )
        import deepl

        self.translator = deepl.Translator(api_key or os.getenv("DEEPL_API_KEY"))

    async def translate(self, text: str) -> str:
        """Translate text using DeepL API."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.translator.translate_text(text, target_lang=self.target_language),
            )
            return str(result)
        except Exception as exc:
            logger.error("DeepL translation error: %s", exc)
            raise TranslationError(f"DeepL translation failed: {exc}") from exc
