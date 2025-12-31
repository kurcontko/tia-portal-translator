"""Tests for the Excel reader."""

from pathlib import Path

from tia_portal_translator.config import Config
from tia_portal_translator.readers import ExcelReader


def test_excel_reader_preserves_falsy_values(tmp_path: Path, sample_workbook):
    """Ensure falsy values like 0/False are preserved, not dropped."""
    source_path = sample_workbook("en-US", "de-DE", [0, "", None, False, "tail"], "input.xlsx")

    config = Config(excel_file=str(source_path))
    reader = ExcelReader(config)
    reader.load_workbook()

    column = reader.find_column_letter("en-US")
    texts = reader.get_source_texts(column)
    assert [text for _, text in texts] == ["0", "", "", "False", "tail"]


def test_excel_reader_skips_formulas(tmp_path: Path, sample_workbook):
    """Ensure formulas can be skipped when configured."""
    source_path = sample_workbook("en-US", "de-DE", ["=SUM(1,2)", "plain"], "input.xlsx")

    config = Config(excel_file=str(source_path), skip_formulas=True)
    reader = ExcelReader(config)
    reader.load_workbook()

    column = reader.find_column_letter("en-US")
    texts = reader.get_source_texts(column)
    assert [text for _, text in texts] == ["", "plain"]
