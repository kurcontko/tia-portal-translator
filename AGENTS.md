# TIA Portal Translator

## Project Summary
- Async CLI tool that translates TIA Portal Excel exports using OpenAI, DeepL, Google Cloud, or free Google Translate.
- Root entrypoint: `run_translator.py` (kept for direct CLI usage).
- Source layout: `src/` package with modular services/readers/writers/pipeline.

## Structure
- `run_translator.py`: Entry point wrapper to run the CLI.
- `src/tia_portal_translator/cli.py`: CLI parsing and orchestration.
- `src/tia_portal_translator/pipeline.py`: Translation pipeline (chunking, wrapping, IO flow).
- `src/tia_portal_translator/services/`: Provider implementations.
- `src/tia_portal_translator/readers/`: Excel input reader.
- `src/tia_portal_translator/writers/`: Excel output writer.
- `src/tia_portal_translator/cache/`: Cache backends and factory.
- `requirements.txt` and `pyproject.toml`: Dependencies (pip + uv).

## Common Commands

### Install (pip)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional editable install (enables `python -m tia_portal_translator`):
```bash
pip install -e .
```

### Install (uv)
```bash
uv venv
uv pip install -r requirements.txt
```

### Common Make targets
```bash
make lint
make typecheck
make test
make build
```

### Run
```bash
python run_translator.py --service openai --source en-US --target de-DE
python run_translator.py --service google-free --source en-US --target de-DE
```

### Build (PyInstaller)
```bash
pyinstaller --onefile --name Translator run_translator.py
```

### Lint
```bash
ruff check .
```
