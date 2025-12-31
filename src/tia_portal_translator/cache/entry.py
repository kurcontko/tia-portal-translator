from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class CacheEntry:
    """Represents a cached translation entry."""

    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    service: str
    timestamp: datetime
    hash_key: str

    def is_expired(self, ttl_hours: int = 24 * 7) -> bool:
        """Check if cache entry is expired (default: 1 week)."""
        return datetime.now() - self.timestamp > timedelta(hours=ttl_hours)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        """Create from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
