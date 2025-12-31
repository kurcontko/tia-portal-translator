import logging
import os
import tempfile
from pathlib import Path
from typing import List, Tuple

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from tia_portal_translator.config import Config

logger = logging.getLogger(__name__)


class ExcelWriter:
    """Write translated data into the Excel workbook."""

    def __init__(self, config: Config, workbook: Workbook, worksheet: Worksheet) -> None:
        self.config = config
        self.workbook = workbook
        self.worksheet = worksheet

    def write_translations(self, translations: List[Tuple[int, str]], target_column: str) -> None:
        """Write translations to the target column."""
        for row_num, translation in translations:
            self.worksheet[f"{target_column}{row_num}"].value = translation

    def save_workbook(self) -> None:
        """Save the workbook to the output file."""
        output_path = Path(self.config.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        temp_file = tempfile.NamedTemporaryFile(
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=output_path.suffix,
            delete=False,
        )
        temp_path = Path(temp_file.name)
        temp_file.close()

        try:
            self.workbook.save(temp_path)
            os.replace(temp_path, output_path)
            logger.info("Saved translated workbook: %s", output_path)
        except Exception:
            if temp_path.exists():
                os.remove(temp_path)
            raise
