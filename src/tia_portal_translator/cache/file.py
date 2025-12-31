import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

from tia_portal_translator.cache.base import TranslationCache
from tia_portal_translator.cache.entry import CacheEntry

logger = logging.getLogger(__name__)


class FileCache(TranslationCache):
    """File-based translation cache using JSON."""

    def __init__(self, cache_dir: str, ttl_hours: int = 24 * 7):
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        self.hits = 0
        self.misses = 0

        os.makedirs(cache_dir, exist_ok=True)
        logger.info("File cache initialized: %s", cache_dir)

    def _get_cache_file_path(self, hash_key: str) -> str:
        """Get cache file path for hash key."""
        return os.path.join(self.cache_dir, f"{hash_key}.json")

    async def get(self, text: str, source_lang: str, target_lang: str, service: str) -> Optional[str]:
        """Get cached translation."""
        hash_key = self._generate_hash(text, source_lang, target_lang, service)
        cache_file = self._get_cache_file_path(hash_key)

        if os.path.exists(cache_file):
            try:
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)

                entry = CacheEntry.from_dict(data)

                if not entry.is_expired(self.ttl_hours):
                    self.hits += 1
                    logger.debug("File cache hit for: %s...", text[:50])
                    return entry.translated_text

                os.remove(cache_file)
                logger.debug("File cache entry expired for: %s...", text[:50])

            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning("Corrupted cache file %s: %s", cache_file, exc)
                os.remove(cache_file)

        self.misses += 1
        logger.debug("File cache miss for: %s...", text[:50])
        return None

    async def set(self, text: str, translation: str, source_lang: str, target_lang: str, service: str) -> None:
        """Store translation in cache."""
        hash_key = self._generate_hash(text, source_lang, target_lang, service)
        cache_file = self._get_cache_file_path(hash_key)

        entry = CacheEntry(
            source_text=text,
            translated_text=translation,
            source_language=source_lang,
            target_language=target_lang,
            service=service,
            timestamp=datetime.now(),
            hash_key=hash_key,
        )

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)

        logger.debug("File cached translation for: %s...", text[:50])

    async def clear(self) -> None:
        """Clear all cache entries."""
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json"):
                os.remove(os.path.join(self.cache_dir, filename))

        self.hits = 0
        self.misses = 0
        logger.info("File cache cleared")

    async def cleanup_expired(self) -> int:
        """Remove expired cache files."""
        expired_count = 0

        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json"):
                cache_file = os.path.join(self.cache_dir, filename)
                try:
                    with open(cache_file, encoding="utf-8") as f:
                        data = json.load(f)

                    entry = CacheEntry.from_dict(data)
                    if entry.is_expired(self.ttl_hours):
                        os.remove(cache_file)
                        expired_count += 1

                except (json.JSONDecodeError, KeyError, ValueError):
                    os.remove(cache_file)
                    expired_count += 1

        logger.info("Cleaned up %s expired file cache entries", expired_count)
        return expired_count

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_files = len([f for f in os.listdir(self.cache_dir) if f.endswith(".json")])
        cache_size = sum(
            os.path.getsize(os.path.join(self.cache_dir, f))
            for f in os.listdir(self.cache_dir)
            if f.endswith(".json")
        )

        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "type": "file",
            "cache_dir": self.cache_dir,
            "total_files": total_files,
            "cache_size_mb": f"{cache_size / (1024 * 1024):.2f}",
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total_requests,
        }
