from tia_portal_translator.cache.base import TranslationCache
from tia_portal_translator.cache.file import FileCache
from tia_portal_translator.cache.hybrid import HybridCache
from tia_portal_translator.cache.memory import MemoryCache
from tia_portal_translator.cache.sqlite import SQLiteCache


class CacheFactory:
    """Factory for creating different types of caches."""

    @staticmethod
    def create_cache(cache_type: str, **kwargs) -> TranslationCache:
        """Create a cache instance based on type."""
        if cache_type == "memory":
            return MemoryCache(**kwargs)
        if cache_type == "sqlite":
            return SQLiteCache(**kwargs)
        if cache_type == "file":
            return FileCache(**kwargs)
        if cache_type == "hybrid":
            ttl_hours = kwargs.get("ttl_hours", 24 * 7)
            memory_cache = MemoryCache(max_size=kwargs.get("memory_size", 1000), ttl_hours=ttl_hours)
            db_path = kwargs.get("db_path")
            if not db_path:
                raise ValueError("db_path is required for hybrid cache")
            persistent_cache = SQLiteCache(db_path=db_path, ttl_hours=ttl_hours)
            return HybridCache(memory_cache, persistent_cache)
        raise ValueError(f"Unknown cache type: {cache_type}")
