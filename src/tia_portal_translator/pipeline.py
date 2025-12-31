import csv
import json
import logging
import textwrap
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Optional, Union
from uuid import uuid4

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
    error: Optional[str] = None


@dataclass
class CacheTotals:
    hits: int = 0
    misses: int = 0
    available: bool = False

    def add(self, cache_hits: Optional[int], cache_misses: Optional[int]) -> None:
        if cache_hits is None or cache_misses is None:
            return
        self.available = True
        self.hits += cache_hits
        self.misses += cache_misses


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


def _error_message(event: str, detail: str) -> str:
    return f"{event}: {detail}"


def _log_context(run_id: str, chunk_id: Optional[Union[int, str]] = None) -> str:
    chunk_value = "-" if chunk_id is None else chunk_id
    return f"run_id={run_id} chunk_id={chunk_value}"


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
    run_id: str,
    chunk_index: int,
    results: list[TranslationResult],
    latency: float,
    cache_hits: Optional[int],
    cache_misses: Optional[int],
) -> None:
    translated, skipped, failed = _count_results(results)
    cache_hits_value = str(cache_hits) if cache_hits is not None else "n/a"
    cache_misses_value = str(cache_misses) if cache_misses is not None else "n/a"
    logger.info(
        "%s event=chunk_metrics translated=%s skipped=%s failed=%s latency=%.2fs cache_hits=%s cache_misses=%s",
        _log_context(run_id, chunk_index),
        translated,
        skipped,
        failed,
        latency,
        cache_hits_value,
        cache_misses_value,
    )


def _log_run_cache_metrics(run_id: str, cache_totals: CacheTotals) -> None:
    if cache_totals.available:
        cache_hits_value = str(cache_totals.hits)
        cache_misses_value = str(cache_totals.misses)
    else:
        cache_hits_value = "n/a"
        cache_misses_value = "n/a"
    logger.info(
        "%s event=cache_metrics cache_hits=%s cache_misses=%s",
        _log_context(run_id),
        cache_hits_value,
        cache_misses_value,
    )


def _consume_service_metrics(translation_service: TranslationService) -> tuple[Optional[int], Optional[int]]:
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

    def __init__(
        self,
        config: Config,
        translation_service: TranslationService,
        run_id: Optional[str] = None,
    ) -> None:
        self.config = config
        self.translation_service = translation_service
        self.reader = ExcelReader(config)
        self.run_id = run_id or uuid4().hex[:12]

    async def translate_project(self, source_language: str, target_language: str) -> None:
        run_id = self.run_id
        cache_totals = CacheTotals()
        try:
            logger.info(
                "%s event=translation_start source=%s target=%s",
                _log_context(run_id),
                source_language,
                target_language,
            )

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

            logger.info(
                "%s event=columns_resolved source_column=%s target_column=%s",
                _log_context(run_id),
                source_column,
                target_column,
            )

            source_texts = self.reader.get_source_texts(source_column)
            logger.info(
                "%s event=texts_loaded total=%s",
                _log_context(run_id),
                len(source_texts),
            )

            results: list[TranslationResult] = []
            for i in range(0, len(source_texts), self.config.chunk_size):
                chunk = source_texts[i : i + self.config.chunk_size]
                chunk_index = i // self.config.chunk_size + 1
                logger.info(
                    "%s event=chunk_start size=%s",
                    _log_context(run_id, chunk_index),
                    len(chunk),
                )
                chunk_start = perf_counter()

                texts_to_translate = [text for _, text in chunk]

                try:
                    batch_result = await self.translation_service.translate_batch(texts_to_translate)
                    translated_texts: list[Union[str, Exception]] = [
                        item if isinstance(item, (str, Exception)) else Exception(str(item))
                        for item in batch_result
                    ]

                except Exception as exc:
                    error_detail = _format_error(exc)
                    logger.error(
                        "%s event=chunk_translate_error error=%s",
                        _log_context(run_id, chunk_index),
                        error_detail,
                    )
                    cache_hits, cache_misses = _consume_service_metrics(self.translation_service)
                    cache_totals.add(cache_hits, cache_misses)
                    error_message = _error_message("chunk_translate_error", error_detail)
                    if self.config.fail_fast:
                        chunk_failures = [
                            TranslationResult(row_num, source_text, "", error_message)
                            for row_num, source_text in chunk
                        ]
                        _log_chunk_metrics(
                            run_id,
                            chunk_index,
                            chunk_failures,
                            perf_counter() - chunk_start,
                            cache_hits,
                            cache_misses,
                        )
                        raise
                    chunk_failures = [
                        TranslationResult(row_num, source_text, "", error_message)
                        for row_num, source_text in chunk
                    ]
                    results.extend(chunk_failures)
                    _log_chunk_metrics(
                        run_id,
                        chunk_index,
                        chunk_failures,
                        perf_counter() - chunk_start,
                        cache_hits,
                        cache_misses,
                    )
                    continue

                cache_hits, cache_misses = _consume_service_metrics(self.translation_service)
                cache_totals.add(cache_hits, cache_misses)
                if len(translated_texts) != len(chunk):
                    provider_name = getattr(self.translation_service, "service_name", None)
                    if not provider_name:
                        provider_name = self.translation_service.__class__.__name__
                    error_detail = (
                        f"provider={provider_name} expected {len(chunk)} items, "
                        f"got {len(translated_texts)}"
                    )
                    logger.error(
                        "%s event=chunk_size_mismatch error=%s",
                        _log_context(run_id, chunk_index),
                        error_detail,
                    )
                    error_message = _error_message("chunk_size_mismatch", error_detail)
                    chunk_failures = [
                        TranslationResult(row_num, source_text, "", error_message)
                        for row_num, source_text in chunk
                    ]
                    _log_chunk_metrics(
                        run_id,
                        chunk_index,
                        chunk_failures,
                        perf_counter() - chunk_start,
                        cache_hits,
                        cache_misses,
                    )
                    if self.config.fail_fast:
                        raise ValueError(error_message)
                    results.extend(chunk_failures)
                    continue

                batch_results: list[TranslationResult] = []
                for (row_num, source_text), translation in zip(chunk, translated_texts):
                    item_error: Optional[str] = None
                    if isinstance(translation, Exception):
                        if self.config.fail_fast:
                            raise translation
                        error_detail = _format_error(translation)
                        item_error = _error_message("item_translate_error", error_detail)
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
                        error=item_error,
                    )
                    batch_results.append(result)

                _log_chunk_metrics(
                    run_id,
                    chunk_index,
                    batch_results,
                    perf_counter() - chunk_start,
                    cache_hits,
                    cache_misses,
                )
                results.extend(batch_results)

            writer.write_translations(
                [(result.row_num, result.translated_text) for result in results],
                target_column,
            )
            writer.save_workbook()

            total = len(results)
            translated, skipped, failed = _count_results(results)
            logger.info(
                "%s event=translation_summary total=%s translated=%s skipped=%s failed=%s",
                _log_context(run_id),
                total,
                translated,
                skipped,
                failed,
            )

            if self.config.report_path:
                try:
                    _write_report(results, self.config.report_path)
                    logger.info(
                        "%s event=report_written path=%s",
                        _log_context(run_id),
                        self.config.report_path,
                    )
                except Exception as exc:
                    error_detail = _format_error(exc)
                    logger.error(
                        "%s event=report_write_error error=%s",
                        _log_context(run_id),
                        error_detail,
                    )
                    if self.config.fail_fast:
                        raise

            logger.info("%s event=translation_complete", _log_context(run_id))
        finally:
            _log_run_cache_metrics(run_id, cache_totals)
