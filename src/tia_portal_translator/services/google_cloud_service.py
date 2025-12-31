import asyncio
import logging
import os
from typing import Optional

from tia_portal_translator.services.base import TranslationError, TranslationService

logger = logging.getLogger(__name__)


class GoogleTranslationService(TranslationService):
    """Google Cloud Translation service."""

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
        from google.cloud import translate_v2 as translate

        if api_key:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = api_key
        self.client = translate.Client()

    async def translate(self, text: str) -> str:
        """Translate text using Google Cloud Translate API."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.translate(text, target_language=self.target_language),
            )
            return str(result["translatedText"])
        except Exception as exc:
            logger.error("Google translation error: %s", exc)
            raise TranslationError(f"Google translation failed: {exc}") from exc
