"""Tests for the translation pipeline."""

import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

from tia_portal_translator.config import Config
from tia_portal_translator.pipeline import TranslatorPipeline

from conftest import RecordingTranslationService, FailingBatchService


@pytest.mark.asyncio
async def test_pipeline_translates_in_chunks(tmp_path: Path, sample_workbook):
    """Test that pipeline correctly processes texts in chunks."""
    source_path = sample_workbook("en-US", "de-DE", ["one", "two", "", "four"], "input.xlsx")
    output_path = tmp_path / "output.xlsx"

    config = Config(
        excel_file=str(source_path),
        output_file=str(output_path),
        chunk_size=2,
    )
    service = RecordingTranslationService(suffix="-de")
    pipeline = TranslatorPipeline(config, service)

    await pipeline.translate_project("en-US", "de-DE")

    workbook = load_workbook(output_path)
    sheet = workbook["User Texts"]
    assert sheet["B2"].value == "one-de"
    assert sheet["B3"].value == "two-de"
    assert sheet["B4"].value is None  # Empty cells in Excel are None, not ""
    assert sheet["B5"].value == "four-de"
    assert service.batch_sizes == [2, 2]


@pytest.mark.asyncio
async def test_pipeline_handles_chunk_failure(tmp_path: Path, sample_workbook):
    """Test that pipeline handles translation failures gracefully."""
    source_path = sample_workbook("en-US", "de-DE", ["one", "two"], "input.xlsx")
    output_path = tmp_path / "output.xlsx"

    config = Config(
        excel_file=str(source_path),
        output_file=str(output_path),
        chunk_size=10,
    )
    pipeline = TranslatorPipeline(config, FailingBatchService())

    await pipeline.translate_project("en-US", "de-DE")

    workbook = load_workbook(output_path)
    sheet = workbook["User Texts"]
    assert sheet["B2"].value is None  # Failed translation results in empty cell
    assert sheet["B3"].value is None


@pytest.mark.asyncio
async def test_pipeline_fail_fast_raises(tmp_path: Path, sample_workbook):
    """Test that fail-fast aborts on translation errors."""
    source_path = sample_workbook("en-US", "de-DE", ["one", "two"], "input.xlsx")
    output_path = tmp_path / "output.xlsx"

    config = Config(
        excel_file=str(source_path),
        output_file=str(output_path),
        chunk_size=10,
        fail_fast=True,
    )
    pipeline = TranslatorPipeline(config, FailingBatchService())

    with pytest.raises(RuntimeError):
        await pipeline.translate_project("en-US", "de-DE")


@pytest.mark.asyncio
async def test_pipeline_writes_report(tmp_path: Path, sample_workbook):
    """Test that pipeline emits a JSON report when requested."""
    source_path = sample_workbook("en-US", "de-DE", ["one", "two"], "input.xlsx")
    output_path = tmp_path / "output.xlsx"
    report_path = tmp_path / "report.json"

    config = Config(
        excel_file=str(source_path),
        output_file=str(output_path),
        chunk_size=2,
        report_path=str(report_path),
    )
    pipeline = TranslatorPipeline(config, RecordingTranslationService(suffix="-de"))

    await pipeline.translate_project("en-US", "de-DE")

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["row_num"] == 2
    assert data[0]["translated_text"] == "one-de"
