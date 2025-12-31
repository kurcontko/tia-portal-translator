import asyncio
import inspect
import logging
from typing import Optional

from tia_portal_translator.services.base import TranslationError, TranslationService

logger = logging.getLogger(__name__)


class GoogleTranslateFreeService(TranslationService):
    """Free Google Translate service using googletrans library (no API key required)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        source_language: str = "auto",
        target_language: str = "en",
        cache=None,
        max_concurrent_requests: int = 10,
        request_delay: float = 0.1,
        max_retries: int = 3,
    ) -> None:
        super().__init__(
            api_key,
            source_language,
            target_language,
            cache,
            max_concurrent_requests=max_concurrent_requests,
            request_delay=request_delay,
            max_retries=max_retries,
        )
        try:
            from googletrans import Translator

            self.translator = Translator()
        except ImportError as exc:
            raise TranslationError(
                "googletrans package not installed. "
                "Install it with: pip install googletrans==4.0.2"
            ) from exc

    async def translate(self, text: str) -> str:
        """Translate text using free Google Translate API."""
        try:
            translate_fn = self.translator.translate
            if inspect.iscoroutinefunction(translate_fn):
                result = await translate_fn(text, dest=self.target_language)
            else:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: translate_fn(text, dest=self.target_language),
                )
            return str(result.text)
        except Exception as exc:
            logger.error("Google Translate (free) error: %s", exc)
            raise TranslationError(f"Google Translate (free) failed: {exc}") from exc
