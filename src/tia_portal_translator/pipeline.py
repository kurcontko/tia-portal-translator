import csv
import json
import logging
import textwrap
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from tia_portal_translator.config import Config
from tia_portal_translator.readers import ExcelReader
from tia_portal_translator.services import TranslationService
from tia_portal_translator.writers import ExcelWriter

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """Capture translation outcomes for reporting and summary."""

    row_num: int
    source_text: str
    translated_text: str
    error: str | None = None


def apply_line_wrapping(translated_text: str, source_text: str, tolerance: float = 1.2) -> str:
    """Apply line wrapping to match source text line lengths."""
    source_lines = source_text.split("\n")

    if len(source_lines) == 1:
        source_len = len(source_text)
        trans_len = len(translated_text)
        if trans_len > source_len * tolerance:
            target_width = int(source_len * tolerance)
            wrapped = textwrap.wrap(
                translated_text,
                width=max(target_width, 20),
                break_long_words=False,
                break_on_hyphens=False,
            )
            return "\n".join(wrapped) if wrapped else translated_text
        return translated_text

    translated_lines = translated_text.split("\n")
    if len(translated_lines) == len(source_lines):
        wrapped_lines: list[str] = []
        for source_line, trans_line in zip(source_lines, translated_lines):
            if len(source_line) == 0:
                wrapped_lines.append("")
            elif len(trans_line) > len(source_line) * tolerance:
                target_width = int(len(source_line) * tolerance)
                wrapped = textwrap.wrap(
                    trans_line,
                    width=max(target_width, 20),
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                wrapped_lines.extend(wrapped if wrapped else [trans_line])
            else:
                wrapped_lines.append(trans_line)
        return "\n".join(wrapped_lines)

    return translated_text


def _format_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _count_results(results: list[TranslationResult]) -> tuple[int, int, int]:
    translated = 0
    skipped = 0
    failed = 0
    for result in results:
        if result.error:
            failed += 1
        elif not result.source_text.strip():
            skipped += 1
        else:
            translated += 1
    return translated, skipped, failed


def _log_chunk_metrics(
    chunk_index: int,
    results: list[TranslationResult],
    latency: float,
    cache_hits: int | None,
    cache_misses: int | None,
) -> None:
    translated, skipped, failed = _count_results(results)
    cache_message = (
        f"cache hits/misses {cache_hits}/{cache_misses}"
        if cache_hits is not None and cache_misses is not None
        else "cache hits/misses n/a"
    )
    logger.info(
        "Chunk %s metrics: %s translated, %s skipped, %s failed, %.2fs latency, %s",
        chunk_index,
        translated,
        skipped,
        failed,
        latency,
        cache_message,
    )


def _consume_service_metrics(translation_service: TranslationService) -> tuple[int | None, int | None]:
    if not hasattr(translation_service, "consume_batch_metrics"):
        return None, None
    batch_metrics = translation_service.consume_batch_metrics()
    cache = getattr(translation_service, "cache", None)
    if not cache:
        return None, None
    return batch_metrics.cache_hits, batch_metrics.cache_misses


def _write_report(results: list[TranslationResult], report_path: str) -> None:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    payload = [
        {
            "row_num": result.row_num,
            "source_text": result.source_text,
            "translated_text": result.translated_text,
            "error": result.error,
        }
        for result in results
    ]

    if suffix == ".json":
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    if suffix == ".csv":
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["row_num", "source_text", "translated_text", "error"],
            )
            writer.writeheader()
            writer.writerows(payload)
        return

    raise ValueError("Report path must end with .json or .csv")


class TranslatorPipeline:
    """Orchestrates reading, translating, and writing workbook data."""

    def __init__(self, config: Config, translation_service: TranslationService) -> None:
        self.config = config
        self.translation_service = translation_service
        self.reader = ExcelReader(config)

    async def translate_project(self, source_language: str, target_language: str) -> None:
        logger.info("Starting translation from %s to %s", source_language, target_language)

        self.reader.load_workbook()
        if not self.reader.workbook or not self.reader.worksheet:
            raise ValueError("Workbook not loaded")

        writer = ExcelWriter(self.config, self.reader.workbook, self.reader.worksheet)

        source_column = self.reader.find_column_letter(source_language)
        target_column = self.reader.find_column_letter(target_language)

        if not source_column:
            raise ValueError(f"Source column '{source_language}' not found")
        if not target_column:
            raise ValueError(f"Target column '{target_language}' not found")

        logger.info("Source column: %s, Target column: %s", source_column, target_column)

        source_texts = self.reader.get_source_texts(source_column)
        logger.info("Found %s texts to translate", len(source_texts))

        results: list[TranslationResult] = []
        for i in range(0, len(source_texts), self.config.chunk_size):
            chunk = source_texts[i : i + self.config.chunk_size]
            chunk_index = i // self.config.chunk_size + 1
            logger.info(
                "Processing chunk %s (%s items)",
                chunk_index,
                len(chunk),
            )
            chunk_start = perf_counter()

            texts_to_translate = [text for _, text in chunk]

            try:
                translated_texts = await self.translation_service.translate_batch(texts_to_translate)

            except Exception as exc:
                logger.error("Error translating chunk: %s", exc)
                cache_hits, cache_misses = _consume_service_metrics(self.translation_service)
                if self.config.fail_fast:
                    chunk_results = [
                        TranslationResult(row_num, source_text, "", _format_error(exc))
                        for row_num, source_text in chunk
                    ]
                    _log_chunk_metrics(
                        chunk_index,
                        chunk_results,
                        perf_counter() - chunk_start,
                        cache_hits,
                        cache_misses,
                    )
                    raise
                error_message = _format_error(exc)
                chunk_results = [
                    TranslationResult(row_num, source_text, "", error_message)
                    for row_num, source_text in chunk
                ]
                results.extend(chunk_results)
                _log_chunk_metrics(
                    chunk_index,
                    chunk_results,
                    perf_counter() - chunk_start,
                    cache_hits,
                    cache_misses,
                )
                continue

            cache_hits, cache_misses = _consume_service_metrics(self.translation_service)

            chunk_results: list[TranslationResult] = []
            for (row_num, source_text), translation in zip(chunk, translated_texts):
                error_message = None
                if isinstance(translation, Exception):
                    if self.config.fail_fast:
                        raise translation
                    error_message = _format_error(translation)
                    translation_text = ""
                else:
                    translation_text = translation

                if self.config.preserve_line_lengths:
                    translation_text = apply_line_wrapping(
                        translation_text,
                        source_text,
                        self.config.line_length_tolerance,
                    )

                result = TranslationResult(
                    row_num=row_num,
                    source_text=source_text,
                    translated_text=translation_text,
                    error=error_message,
                )
                results.append(result)
                chunk_results.append(result)
            _log_chunk_metrics(
                chunk_index,
                chunk_results,
                perf_counter() - chunk_start,
                cache_hits,
                cache_misses,
            )

        writer.write_translations(
            [(result.row_num, result.translated_text) for result in results],
            target_column,
        )
        writer.save_workbook()

        total = len(results)
        translated, skipped, failed = _count_results(results)
        logger.info(
            "Translation summary: %s total, %s translated, %s skipped, %s failed",
            total,
            translated,
            skipped,
            failed,
        )

        if self.config.report_path:
            try:
                _write_report(results, self.config.report_path)
                logger.info("Report written to %s", self.config.report_path)
            except Exception as exc:
                logger.error("Failed to write report: %s", exc)
                if self.config.fail_fast:
                    raise

        logger.info("Translation completed successfully!")
