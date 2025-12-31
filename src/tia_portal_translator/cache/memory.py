import logging
from datetime import datetime
from typing import Any, Dict, Optional

from tia_portal_translator.cache.base import TranslationCache
from tia_portal_translator.cache.entry import CacheEntry

logger = logging.getLogger(__name__)


class MemoryCache(TranslationCache):
    """In-memory translation cache using dictionary."""

    def __init__(self, max_size: int = 10000, ttl_hours: int = 24 * 7):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.ttl_hours = ttl_hours
        self.hits = 0
        self.misses = 0

    async def get(self, text: str, source_lang: str, target_lang: str, service: str) -> Optional[str]:
        """Get cached translation."""
        hash_key = self._generate_hash(text, source_lang, target_lang, service)

        if hash_key in self.cache:
            entry = self.cache[hash_key]
            if not entry.is_expired(self.ttl_hours):
                self.hits += 1
                logger.debug("Cache hit for: %s...", text[:50])
                return entry.translated_text
            del self.cache[hash_key]
            logger.debug("Cache entry expired for: %s...", text[:50])

        self.misses += 1
        logger.debug("Cache miss for: %s...", text[:50])
        return None

    async def set(self, text: str, translation: str, source_lang: str, target_lang: str, service: str) -> None:
        """Store translation in cache."""
        hash_key = self._generate_hash(text, source_lang, target_lang, service)

        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_key]
            logger.debug("Cache full, removed oldest entry")

        entry = CacheEntry(
            source_text=text,
            translated_text=translation,
            source_language=source_lang,
            target_language=target_lang,
            service=service,
            timestamp=datetime.now(),
            hash_key=hash_key,
        )

        self.cache[hash_key] = entry
        logger.debug("Cached translation for: %s...", text[:50])

    async def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Memory cache cleared")

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "type": "memory",
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total_requests,
        }
