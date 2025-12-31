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
        ttl_hours = kwargs.get("ttl_hours", 24 * 7)
        if cache_type == "memory":
            max_size = kwargs.get("memory_size", kwargs.get("max_size"))
            if max_size is None:
                return MemoryCache(ttl_hours=ttl_hours)
            return MemoryCache(max_size=max_size, ttl_hours=ttl_hours)
        if cache_type == "sqlite":
            db_path = kwargs.get("db_path")
            if not db_path:
                raise ValueError("db_path is required for sqlite cache")
            return SQLiteCache(db_path=db_path, ttl_hours=ttl_hours)
        if cache_type == "file":
            cache_dir = kwargs.get("cache_dir")
            if not cache_dir:
                raise ValueError("cache_dir is required for file cache")
            return FileCache(cache_dir=cache_dir, ttl_hours=ttl_hours)
        if cache_type == "hybrid":
            memory_cache = MemoryCache(max_size=kwargs.get("memory_size", 1000), ttl_hours=ttl_hours)
            db_path = kwargs.get("db_path")
            if not db_path:
                raise ValueError("db_path is required for hybrid cache")
            persistent_cache = SQLiteCache(db_path=db_path, ttl_hours=ttl_hours)
            return HybridCache(memory_cache, persistent_cache)
        raise ValueError(f"Unknown cache type: {cache_type}")
