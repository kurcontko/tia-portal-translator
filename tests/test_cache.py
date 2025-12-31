from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tia_portal_translator.cache import (
    CacheFactory,
    CacheManager,
    FileCache,
    HybridCache,
    MemoryCache,
    SQLiteCache,
)


@pytest.mark.asyncio
async def test_memory_cache_get_set_and_expire():
    cache = MemoryCache(max_size=10, ttl_hours=1)
    await cache.set("hello", "hola", "en", "es", "svc")
    assert await cache.get("hello", "en", "es", "svc") == "hola"

    hash_key = cache._generate_hash("hello", "en", "es", "svc")
    cache.cache[hash_key].timestamp = datetime.now() - timedelta(hours=2)

    assert await cache.get("hello", "en", "es", "svc") is None
    assert hash_key not in cache.cache


@pytest.mark.asyncio
async def test_memory_cache_eviction():
    cache = MemoryCache(max_size=1)
    await cache.set("first", "1", "en", "es", "svc")
    old_key = cache._generate_hash("first", "en", "es", "svc")
    cache.cache[old_key].timestamp = datetime.now() - timedelta(hours=1)

    await cache.set("second", "2", "en", "es", "svc")
    assert len(cache.cache) == 1
    assert await cache.get("first", "en", "es", "svc") is None
    assert await cache.get("second", "en", "es", "svc") == "2"


@pytest.mark.asyncio
async def test_file_cache_hit_and_expire(tmp_path: Path):
    cache = FileCache(cache_dir=str(tmp_path), ttl_hours=1)
    await cache.set("hello", "hola", "en", "es", "svc")
    assert await cache.get("hello", "en", "es", "svc") == "hola"

    hash_key = cache._generate_hash("hello", "en", "es", "svc")
    cache_file = tmp_path / f"{hash_key}.json"
    data = json.loads(cache_file.read_text())
    data["timestamp"] = (datetime.now() - timedelta(hours=2)).isoformat()
    cache_file.write_text(json.dumps(data))

    assert await cache.get("hello", "en", "es", "svc") is None
    assert not cache_file.exists()


@pytest.mark.asyncio
async def test_file_cache_cleanup_expired_and_corrupt(tmp_path: Path):
    cache = FileCache(cache_dir=str(tmp_path), ttl_hours=1)
    await cache.set("fresh", "ok", "en", "es", "svc")
    await cache.set("old", "stale", "en", "es", "svc")

    old_key = cache._generate_hash("old", "en", "es", "svc")
    old_file = tmp_path / f"{old_key}.json"
    data = json.loads(old_file.read_text())
    data["timestamp"] = (datetime.now() - timedelta(hours=2)).isoformat()
    old_file.write_text(json.dumps(data))

    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{not json")

    expired_count = await cache.cleanup_expired()
    assert expired_count == 2
    assert not old_file.exists()
    assert not corrupt_file.exists()


@pytest.mark.asyncio
async def test_sqlite_cache_hit_and_expire(tmp_path: Path):
    db_path = tmp_path / "cache.db"
    cache = SQLiteCache(db_path=str(db_path), ttl_hours=1)
    await cache.set("hello", "hola", "en", "es", "svc")
    assert await cache.get("hello", "en", "es", "svc") == "hola"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE translations SET timestamp = ?",
            ((datetime.now() - timedelta(hours=2)).isoformat(),),
        )
        conn.commit()

    assert await cache.get("hello", "en", "es", "svc") is None
    with sqlite3.connect(db_path) as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
    assert remaining == 0


@pytest.mark.asyncio
async def test_sqlite_cache_cleanup_expired(tmp_path: Path):
    db_path = tmp_path / "cache.db"
    cache = SQLiteCache(db_path=str(db_path), ttl_hours=1)
    await cache.set("old", "stale", "en", "es", "svc")
    await cache.set("fresh", "ok", "en", "es", "svc")

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE translations SET timestamp = ? WHERE source_text = ?",
            ((datetime.now() - timedelta(hours=2)).isoformat(), "old"),
        )
        conn.commit()

    expired_count = await cache.cleanup_expired()
    assert expired_count == 1
    with sqlite3.connect(db_path) as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
    assert remaining == 1


@pytest.mark.asyncio
async def test_hybrid_cache_promotes_from_persistent():
    memory_cache = MemoryCache()
    persistent_cache = MemoryCache()
    cache = HybridCache(memory_cache, persistent_cache)

    await persistent_cache.set("hello", "hola", "en", "es", "svc")
    assert await cache.get("hello", "en", "es", "svc") == "hola"
    assert len(memory_cache.cache) == 1


@pytest.mark.asyncio
async def test_cache_factory_creates_expected_types(tmp_path: Path):
    memory_cache = CacheFactory.create_cache("memory")
    assert isinstance(memory_cache, MemoryCache)

    file_cache = CacheFactory.create_cache("file", cache_dir=str(tmp_path))
    assert isinstance(file_cache, FileCache)

    sqlite_cache = CacheFactory.create_cache("sqlite", db_path=str(tmp_path / "cache.db"))
    assert isinstance(sqlite_cache, SQLiteCache)

    hybrid_cache = CacheFactory.create_cache("hybrid", db_path=str(tmp_path / "hybrid.db"))
    assert isinstance(hybrid_cache, HybridCache)

    with pytest.raises(ValueError):
        CacheFactory.create_cache("hybrid")


@pytest.mark.asyncio
async def test_cache_manager_exports_and_imports(tmp_path: Path):
    db_path = tmp_path / "cache.db"
    cache = SQLiteCache(db_path=str(db_path))
    await cache.set("hello", "hola", "en", "es", "svc")

    export_path = tmp_path / "export.json"
    manager = CacheManager(cache)
    await manager.export_cache(str(export_path))
    assert export_path.exists()

    new_db_path = tmp_path / "new.db"
    new_cache = SQLiteCache(db_path=str(new_db_path))
    new_manager = CacheManager(new_cache)
    await new_manager.import_cache(str(export_path))

    with sqlite3.connect(new_db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
    assert count == 1


@pytest.mark.asyncio
async def test_cache_manager_print_stats(capsys):
    cache = MemoryCache()
    manager = CacheManager(cache)
    await manager.print_stats()
    out = capsys.readouterr().out
    assert "Cache Statistics" in out
