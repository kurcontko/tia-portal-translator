from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from platformdirs import user_cache_dir


@dataclass
class Config:
    """Configuration settings for the translator."""

    excel_file: str = "TIAProjectTexts.xlsx"
    sheet_name: str = "User Texts"
    output_file: Optional[str] = None
    max_concurrent_requests: int = 10
    request_delay: float = 0.1  # seconds between requests
    max_retries: int = 3
    chunk_size: int = 100
    fail_fast: bool = False
    report_path: Optional[str] = None
    skip_formulas: bool = False
    # Line wrapping configuration
    preserve_line_lengths: bool = False
    line_length_tolerance: float = 1.2  # Allow 20% longer lines
    # Caching configuration
    cache_enabled: bool = True
    cache_type: str = "hybrid"  # memory, sqlite, file, hybrid
    cache_ttl_hours: int = 24 * 7  # 1 week default
    cache_max_memory_size: int = 10000
    cache_db_path: str = ""
    cache_dir: str = ""

    def __post_init__(self) -> None:
        if self.output_file is None:
            self.output_file = f"{Path(self.excel_file).stem}_translated.xlsx"
        if not self.cache_db_path or not self.cache_dir:
            base_cache_dir = Path(
                user_cache_dir("tia-portal-translator", "tia-portal-translator")
            )
            if not self.cache_db_path:
                self.cache_db_path = str(base_cache_dir / "translation_cache.db")
            if not self.cache_dir:
                self.cache_dir = str(base_cache_dir / "translation_cache")
