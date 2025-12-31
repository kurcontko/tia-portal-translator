import csv
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

import tia_portal_translator.cli as cli
from conftest import RecordingTranslationService


@pytest.mark.asyncio
async def test_cli_smoke_translates_workbook_and_report(tmp_path: Path, sample_workbook, monkeypatch):
    source_path = sample_workbook("en-US", "de-DE", ["one", "", "three"], "input.xlsx")
    output_path = tmp_path / "output.xlsx"
    report_path = tmp_path / "report.csv"

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        cli.TranslationServiceFactory,
        "create_service",
        lambda *args, **kwargs: RecordingTranslationService(suffix="-de"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--service",
            "google-free",
            "--source",
            "en-US",
            "--target",
            "de-DE",
            "--file",
            str(source_path),
            "--output",
            str(output_path),
            "--report",
            str(report_path),
            "--cache-type",
            "none",
        ],
    )

    await cli.main()

    workbook = load_workbook(output_path)
    sheet = workbook["User Texts"]
    assert sheet["B2"].value == "one-de"
    assert sheet["B3"].value is None
    assert sheet["B4"].value == "three-de"

    with report_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert rows[0]["translated_text"] == "one-de"
