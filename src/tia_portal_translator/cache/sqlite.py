import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from tia_portal_translator.cache.base import TranslationCache

logger = logging.getLogger(__name__)


class SQLiteCache(TranslationCache):
    """SQLite-based persistent translation cache."""

    def __init__(self, db_path: str, ttl_hours: int = 24 * 7):
        self.db_path = db_path
        self.ttl_hours = ttl_hours
        self.hits = 0
        self.misses = 0
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS translations (
                    hash_key TEXT PRIMARY KEY,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_language TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    service TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp ON translations(timestamp)
                """
            )
            conn.commit()
        logger.info("SQLite cache initialized: %s", self.db_path)

    async def get(self, text: str, source_lang: str, target_lang: str, service: str) -> Optional[str]:
        """Get cached translation."""
        hash_key = self._generate_hash(text, source_lang, target_lang, service)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT translated_text, timestamp FROM translations WHERE hash_key = ?",
                (hash_key,),
            )
            result = cursor.fetchone()

            if result:
                translated_text, timestamp_str = result
                timestamp = datetime.fromisoformat(timestamp_str)

                if datetime.now() - timestamp <= timedelta(hours=self.ttl_hours):
                    self.hits += 1
                    logger.debug("SQLite cache hit for: %s...", text[:50])
                    return translated_text

                conn.execute("DELETE FROM translations WHERE hash_key = ?", (hash_key,))
                conn.commit()
                logger.debug("SQLite cache entry expired for: %s...", text[:50])

            self.misses += 1
            logger.debug("SQLite cache miss for: %s...", text[:50])
            return None

    async def set(self, text: str, translation: str, source_lang: str, target_lang: str, service: str) -> None:
        """Store translation in cache."""
        hash_key = self._generate_hash(text, source_lang, target_lang, service)
        timestamp = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO translations
                (hash_key, source_text, translated_text, source_language, target_language, service, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (hash_key, text, translation, source_lang, target_lang, service, timestamp),
            )
            conn.commit()

        logger.debug("SQLite cached translation for: %s...", text[:50])

    async def clear(self) -> None:
        """Clear all cache entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM translations")
            conn.commit()

        self.hits = 0
        self.misses = 0
        logger.info("SQLite cache cleared")

    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed entries."""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM translations WHERE timestamp < ?",
                (cutoff_time,),
            )
            expired_count = cursor.fetchone()[0]
            conn.execute("DELETE FROM translations WHERE timestamp < ?", (cutoff_time,))
            conn.commit()

        logger.info("Cleaned up %s expired cache entries", expired_count)
        return expired_count

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM translations")
            total_entries = cursor.fetchone()[0]

            cursor = conn.execute(
                """
                SELECT service, COUNT(*) FROM translations
                GROUP BY service
                """
            )
            by_service = dict(cursor.fetchall())

        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "type": "sqlite",
            "db_path": self.db_path,
            "total_entries": total_entries,
            "by_service": by_service,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total_requests,
        }
