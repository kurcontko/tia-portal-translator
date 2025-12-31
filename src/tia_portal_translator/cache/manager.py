import json
import logging
import sqlite3

from tia_portal_translator.cache.base import TranslationCache
from tia_portal_translator.cache.sqlite import SQLiteCache

logger = logging.getLogger(__name__)


class CacheManager:
    """Utility class for managing translation caches."""

    def __init__(self, cache: TranslationCache):
        self.cache = cache

    async def print_stats(self) -> None:
        """Print cache statistics."""
        stats = await self.cache.get_stats()
        print("\n📊 Cache Statistics:")
        print("=" * 40)
        for key, value in stats.items():
            print(f"{key.replace('_', ' ').title()}: {value}")

    async def export_cache(self, export_path: str) -> None:
        """Export cache to JSON file (for SQLite cache)."""
        if isinstance(self.cache, SQLiteCache):
            with sqlite3.connect(self.cache.db_path) as conn:
                cursor = conn.execute("SELECT * FROM translations")
                rows = cursor.fetchall()

                export_data = []
                for row in rows:
                    export_data.append(
                        {
                            "hash_key": row[0],
                            "source_text": row[1],
                            "translated_text": row[2],
                            "source_language": row[3],
                            "target_language": row[4],
                            "service": row[5],
                            "timestamp": row[6],
                        }
                    )

                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

                logger.info("Cache exported to %s", export_path)
        else:
            logger.warning("Export only supported for SQLite cache")

    async def import_cache(self, import_path: str) -> None:
        """Import cache from JSON file (for SQLite cache)."""
        if isinstance(self.cache, SQLiteCache):
            with open(import_path, encoding="utf-8") as f:
                import_data = json.load(f)

            with sqlite3.connect(self.cache.db_path) as conn:
                for entry in import_data:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO translations
                        (hash_key, source_text, translated_text, source_language, target_language, service, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            entry["hash_key"],
                            entry["source_text"],
                            entry["translated_text"],
                            entry["source_language"],
                            entry["target_language"],
                            entry["service"],
                            entry["timestamp"],
                        ),
                    )
                conn.commit()

            logger.info("Cache imported from %s", import_path)
        else:
            logger.warning("Import only supported for SQLite cache")
