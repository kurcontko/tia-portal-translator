import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))


# Test fixtures and utilities


class RecordingTranslationService:
    """Mock translation service that records batch sizes."""

    def __init__(self, suffix: str = "-x"):
        self.suffix = suffix
        self.batch_sizes = []

    async def translate_batch(self, texts):
        self.batch_sizes.append(len(texts))
        return [f"{text}{self.suffix}" if text else "" for text in texts]


class FailingBatchService:
    """Mock translation service that always fails."""

    async def translate_batch(self, texts):
        raise RuntimeError("boom")


class ShortBatchService:
    """Mock translation service that returns fewer items than requested."""

    service_name = "short-batch"

    async def translate_batch(self, texts):
        if not texts:
            return []
        return [f"{text}-x" if text else "" for text in texts[:-1]]


class LongBatchService:
    """Mock translation service that returns extra items."""

    service_name = "long-batch"

    async def translate_batch(self, texts):
        return [f"{text}-x" if text else "" for text in texts] + ["extra"]


@pytest.fixture
def sample_workbook(tmp_path: Path):
    """Create a sample Excel workbook for testing."""

    def _create(source_col: str, target_col: str, rows: list, filename: str = "test.xlsx"):
        path = tmp_path / filename
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "User Texts"
        sheet["A1"] = source_col
        sheet["B1"] = target_col

        for idx, value in enumerate(rows, start=2):
            sheet[f"A{idx}"] = value

        workbook.save(path)
        return path

    return _create
