import hashlib
from abc import ABC, abstractmethod
from typing import Any, Optional


class TranslationCache(ABC):
    """Abstract base class for translation caches."""

    @abstractmethod
    async def get(self, text: str, source_lang: str, target_lang: str, service: str) -> Optional[str]:
        """Get cached translation."""
        raise NotImplementedError

    @abstractmethod
    async def set(self, text: str, translation: str, source_lang: str, target_lang: str, service: str) -> None:
        """Store translation in cache."""
        raise NotImplementedError

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        raise NotImplementedError

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        raise NotImplementedError

    def _generate_hash(self, text: str, source_lang: str, target_lang: str, service: str) -> str:
        """Generate hash key for cache entry."""
        content = f"{text}|{source_lang}|{target_lang}|{service}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
