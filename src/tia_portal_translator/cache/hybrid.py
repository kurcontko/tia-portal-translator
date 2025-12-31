import logging
from typing import Any, Optional

from tia_portal_translator.cache.base import TranslationCache

logger = logging.getLogger(__name__)


class HybridCache(TranslationCache):
    """Hybrid cache using memory for hot data and persistent storage for cold data."""

    def __init__(self, memory_cache: TranslationCache, persistent_cache: TranslationCache):
        self.memory_cache = memory_cache
        self.persistent_cache = persistent_cache
        self.hits = 0
        self.misses = 0

    async def get(self, text: str, source_lang: str, target_lang: str, service: str) -> Optional[str]:
        """Get cached translation (check memory first, then persistent)."""
        result = await self.memory_cache.get(text, source_lang, target_lang, service)
        if result:
            self.hits += 1
            logger.debug("Hybrid cache hit (memory) for: %s...", text[:50])
            return result

        result = await self.persistent_cache.get(text, source_lang, target_lang, service)
        if result:
            await self.memory_cache.set(text, result, source_lang, target_lang, service)
            self.hits += 1
            logger.debug("Hybrid cache hit (persistent) for: %s...", text[:50])
            return result

        self.misses += 1
        logger.debug("Hybrid cache miss for: %s...", text[:50])
        return None

    async def set(self, text: str, translation: str, source_lang: str, target_lang: str, service: str) -> None:
        """Store translation in both caches."""
        await self.memory_cache.set(text, translation, source_lang, target_lang, service)
        await self.persistent_cache.set(text, translation, source_lang, target_lang, service)
        logger.debug("Hybrid cached translation for: %s...", text[:50])

    async def clear(self) -> None:
        """Clear both caches."""
        await self.memory_cache.clear()
        await self.persistent_cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Hybrid cache cleared")

    async def get_stats(self) -> dict[str, Any]:
        """Get combined cache statistics."""
        memory_stats = await self.memory_cache.get_stats()
        persistent_stats = await self.persistent_cache.get_stats()

        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "type": "hybrid",
            "memory": memory_stats,
            "persistent": persistent_stats,
            "combined_hits": self.hits,
            "combined_misses": self.misses,
            "combined_hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total_requests,
        }
