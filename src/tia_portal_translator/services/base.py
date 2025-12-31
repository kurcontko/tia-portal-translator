import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import Optional, Union

from asyncio_throttle import Throttler

from tia_portal_translator.cache import TranslationCache

logger = logging.getLogger(__name__)


@dataclass
class BatchMetrics:
    cache_hits: int = 0
    cache_misses: int = 0


class TranslationError(Exception):
    """Custom exception for translation errors."""


TranslationOutcome = Union[str, BaseException]


class TranslationService(ABC):
    """Abstract base class for translation services."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        source_language: str = "auto",
        target_language: str = "en",
        cache: Optional[TranslationCache] = None,
        max_concurrent_requests: int = 10,
        request_delay: float = 0.1,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key
        self.source_language = source_language
        self.target_language = target_language
        self.throttler = Throttler(rate_limit=10, period=1.0)  # 10 requests per second
        self.cache = cache
        self.service_name = self.__class__.__name__.replace("TranslationService", "").lower()
        self.max_concurrent_requests = max(1, max_concurrent_requests)
        self.request_delay = max(0.0, request_delay)
        self.max_retries = max(1, max_retries)
        self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        self._last_batch_metrics = BatchMetrics()

    @abstractmethod
    async def translate(self, text: str) -> str:
        """Translate text to target language."""

    async def translate_batch(self, texts: list[str]) -> list[TranslationOutcome]:
        """Translate a batch of texts with throttling.

        Returns a list of translations or exception instances for failed items.
        """
        self._reset_batch_metrics()
        tasks = []
        for text in texts:
            if text.strip():  # Only translate non-empty texts
                tasks.append(self._translate_with_throttle(text, self._last_batch_metrics))
            else:
                tasks.append(self._return_empty())

        return await asyncio.gather(*tasks, return_exceptions=True)

    def consume_batch_metrics(self) -> BatchMetrics:
        metrics = self._last_batch_metrics
        self._last_batch_metrics = BatchMetrics()
        return metrics

    def _reset_batch_metrics(self) -> None:
        self._last_batch_metrics = BatchMetrics()

    def _get_retry_attempts(self) -> int:
        """Return attempts for the base retry loop (override for provider retries)."""
        return self.max_retries

    async def _perform_translation(self, text: str) -> str:
        """Perform a single translation attempt with delay and throttling."""
        if self.request_delay:
            await asyncio.sleep(self.request_delay)
        throttle_start = perf_counter()
        async with self.throttler:
            throttle_wait = perf_counter() - throttle_start
            if throttle_wait > 0.001:
                logger.debug(
                    "Provider %s throttled for %.3fs",
                    self.service_name,
                    throttle_wait,
                )
            return await self.translate(text)

    async def _cache_result(self, text: str, result: str) -> None:
        if self.cache and result:
            await self.cache.set(
                text,
                result,
                self.source_language,
                self.target_language,
                self.service_name,
            )
            logger.debug("Cached result for %s: %s...", self.service_name, text[:50])

    async def _translate_with_throttle(
        self,
        text: str,
        metrics: Optional[BatchMetrics] = None,
    ) -> str:
        """Translate with caching, throttling and retry logic."""
        if metrics is None:
            metrics = BatchMetrics()
        if self.cache:
            cached_result = await self.cache.get(
                text,
                self.source_language,
                self.target_language,
                self.service_name,
            )
            if cached_result:
                metrics.cache_hits += 1
                logger.debug("Cache hit for %s: %s...", self.service_name, text[:50])
                return cached_result
            metrics.cache_misses += 1

        retry_attempts = max(1, self._get_retry_attempts())

        for attempt in range(retry_attempts):
            async with self._semaphore:
                try:
                    logger.debug(
                        "Provider %s attempt %s/%s for: %s...",
                        self.service_name,
                        attempt + 1,
                        retry_attempts,
                        text[:50],
                    )
                    result = await self._perform_translation(text)
                    await self._cache_result(text, result)
                    return result
                except Exception as exc:
                    if attempt == retry_attempts - 1:
                        logger.error(
                            "Provider %s failed after %s attempts: %s",
                            self.service_name,
                            retry_attempts,
                            exc,
                        )
                        raise TranslationError(f"Translation failed: {exc}") from exc
                    logger.debug(
                        "Provider %s retrying after error on attempt %s/%s: %s",
                        self.service_name,
                        attempt + 1,
                        retry_attempts,
                        exc,
                    )
            # Release semaphore during retry delay to allow other requests
            await asyncio.sleep(2 ** attempt)

        raise TranslationError("Translation failed without retry attempts.")

    async def _return_empty(self) -> str:
        """Return empty string for empty inputs."""
        return ""
