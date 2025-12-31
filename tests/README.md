# Test Suite Organization

This directory contains the test suite for the TIA Portal Translator project.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and test utilities
├── test_excel_reader.py     # Excel reader unit tests
├── test_excel_writer.py     # Excel writer unit tests
├── test_pipeline.py         # Pipeline integration tests
├── test_line_wrapping.py    # Line wrapping unit tests
└── test_services.py         # Service behavior tests
```

## Test Files

### `conftest.py`
Provides shared test fixtures and utilities:
- `RecordingTranslationService`: Mock service that records batch sizes for testing chunking logic
- `FailingBatchService`: Mock service that always fails for error handling tests
- `sample_workbook`: Fixture that creates Excel workbooks for testing

### `test_pipeline.py`
Integration tests for the translation pipeline:
- ✅ `test_pipeline_translates_in_chunks`: Verifies chunking logic and batch processing
- ✅ `test_pipeline_handles_chunk_failure`: Ensures graceful error handling
- ✅ `test_pipeline_fail_fast_raises`: Ensures fail-fast behavior stops on errors
- ✅ `test_pipeline_writes_report`: Ensures JSON report output is produced

### `test_line_wrapping.py`
Unit tests for the line wrapping feature:
- ✅ `test_apply_line_wrapping_wraps_long_lines`: Basic wrapping functionality
- ✅ `test_apply_line_wrapping_preserves_short_text`: No wrapping when not needed
- ✅ `test_apply_line_wrapping_respects_tolerance`: Tolerance parameter control
- ✅ `test_apply_line_wrapping_preserves_existing_newlines`: Multi-line text handling
- ✅ `test_apply_line_wrapping_handles_empty_text`: Edge case handling
- ✅ `test_apply_line_wrapping_no_break_on_words`: Word boundary respect

### `test_excel_reader.py`
Unit tests for the Excel reader:
- ✅ `test_excel_reader_preserves_falsy_values`: Ensures 0/False are preserved
- ✅ `test_excel_reader_skips_formulas`: Ensures formulas can be skipped

### `test_excel_writer.py`
Unit tests for the Excel writer:
- ✅ `test_excel_writer_atomic_save_same_path`: Ensures atomic save behavior

### `test_services.py`
Unit tests for service behavior:
- ✅ `test_translate_batch_respects_max_concurrency`: Enforces concurrency limit

## Running Tests

### Run all tests
```bash
pytest
```

### Run with verbose output
```bash
pytest -v
```

### Run with coverage
```bash
pytest --cov=src/tia_portal_translator --cov-report=term-missing
```

### Run specific test file
```bash
pytest tests/test_pipeline.py
pytest tests/test_line_wrapping.py
```

### Run specific test
```bash
pytest tests/test_pipeline.py::test_pipeline_translates_in_chunks
```

## Test Philosophy

- **Integration tests** (`test_pipeline.py`): Test end-to-end workflows with realistic scenarios
- **Unit tests** (`test_line_wrapping.py`): Test isolated functionality with clear inputs/outputs
- **Fixtures**: Reusable components in `conftest.py` to reduce duplication
- **Clear naming**: Test names describe what they verify
- **Fast execution**: Tests run in < 0.2 seconds

## Future Additions

When adding new tests, consider creating separate files for:
- Cache system tests (`test_cache.py`) - async operations, TTL, persistence
- CLI tests (`test_cli.py`) - argument parsing, command execution

## Coverage

Current coverage: **44%**

Focus areas for improvement:
- Cache implementations (hybrid, SQLite, memory)
- Translation services (OpenAI, DeepL, Google)
- CLI argument handling
- Error scenarios and edge cases
