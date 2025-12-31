# TIA Portal Translator
Modern, async-powered tool for translating TIA Portal texts exported to Excel using
Google Cloud Translate, OpenAI GPT, and DeepL APIs. A legacy script and wrapper
are preserved under `deprecated/`.

## Getting Started

### Prerequisites

- Python 3.9+
- Install dependencies:

```bash
pip install -r requirements.txt
```

Optional editable install (enables `python -m tia_portal_translator`):

```bash
pip install -e .
```

Optional with `uv`:

```bash
uv venv
uv pip install -r requirements.txt
```

### API Keys Setup

Create a `.env` file in the project root with your API keys (not needed for `google-free`):

```env
OPENAI_API_KEY=your_openai_api_key_here
DEEPL_API_KEY=your_deepl_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
```

## Usage

### Basic

```bash
# Free Google Translate (no API key required)
python run_translator.py --service google-free --source en-US --target de-DE

# Module mode (after editable install)
python -m tia_portal_translator --service google-free --source en-US --target de-DE

# OpenAI GPT
python run_translator.py --service openai --source en-US --target de-DE

# DeepL
python run_translator.py --service deepl --source en-US --target fr-FR

# Google Cloud Translate
python run_translator.py --service google --source de-DE --target en-US
```

### Advanced

```bash
python run_translator.py \
  --service openai \
  --source en-US \
  --target de-DE \
  --file custom_texts.xlsx \
  --chunk-size 50 \
  --max-concurrent 5
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--service` | Translation service (openai, gpt, deepl, google, google-free) | Required |
| `--source` | Source language code (e.g., en-US, de-DE) | Required |
| `--target` | Target language code (e.g., en-US, de-DE) | Required |
| `--file` | Input Excel file path | TIAProjectTexts.xlsx |
| `--output` | Output Excel file path | Auto-generated |
| `--sheet` | Excel sheet name | User Texts |
| `--chunk-size` | Texts per processing chunk | 100 |
| `--max-concurrent` | Max concurrent requests | 10 |
| `--preserve-line-lengths` | Wrap translations to match source line lengths | False |
| `--line-length-tolerance` | Line length multiplier (e.g., 1.2 = 20% longer) | 1.2 |
| `--verbose` | Enable verbose logging | False |

## Local LLM Backends (Ollama, MLX-LM, vLLM)

This project can use any OpenAI-compatible server via the `openai` service.
The OpenAI client is configured using environment variables, so local servers
just need to expose `/v1/chat/completions`.

### How this project connects to local servers

Set these env vars before running the CLI:

- `OPENAI_API_BASE`: Base URL that includes `/v1`
- `OPENAI_MODEL`: Model name served by the local runtime
- `OPENAI_API_KEY`: Required by the OpenAI Python client (can be dummy for local servers)

Example:

```bash
export OPENAI_API_BASE=http://localhost:8000/v1
export OPENAI_MODEL=google/gemma-3-4b-it
export OPENAI_API_KEY=wow-such-empty
python tia_portal_translator.py --service openai --source en-US --target de-DE
```

If your server requires an API key (vLLM can), set `OPENAI_API_KEY` to match.

### Model recommendations

For translation quality, prefer Gemma 3 models where available in your
runtime (Ollama/vLLM/MLX). Model naming varies by runtime, so check the model
registry for the exact Gemma 3 identifier it supports.

For paid APIs, recommended defaults are:

- OpenAI: `gpt-4.1` or `gpt-4.1-mini`
- Google: Gemini 3 Flash (well, it requires a Gemini client or an OpenAI-compatible proxy, will be handled in future)

### Ollama (cross-platform)

Personally I hate Ollama, but as it's easy to configure for non-AI people let's mention it.

Ollama provides OpenAI-compatible endpoints. The docs show the OpenAI client configured
with `base_url` as `http://localhost:11434/v1/` and an API key that is required but ignored.

Run a model:

```bash
ollama pull gemma3:4b
```

Use with this project:

```bash
export OPENAI_API_BASE=http://localhost:11434/v1
export OPENAI_MODEL=gemma3:4b
export OPENAI_API_KEY=ollama
python tia_portal_translator.py --service openai --source en-US --target de-DE
```

### vLLM (Linux + GPU)

vLLM provides an OpenAI-compatible server.
Start the server:

```bash
vllm serve google/gemma-3-4b-it --dtype auto --api-key wow-such-empty
```

- Default base URL: `http://localhost:8000/v1`
- The model name is the HF repo ID you pass to `vllm serve`.

Use with this project:

```bash
export OPENAI_API_BASE=http://localhost:8000/v1
export OPENAI_MODEL=google/gemma-3-4b-it
export OPENAI_API_KEY=wow-such-empty
python tia_portal_translator.py --service openai --source en-US --target de-DE
```

### MLX-LM server (macOS, Apple Silicon)

The MLX-LM server exposes a local HTTP API similar to the OpenAI chat API.

Start the server:

```bash
mlx_lm.server --model mlx-community/gemma-3n-E4B-it-lm-4bit
```

- Runs on `localhost:8080`
- Downloads the model from Hugging Face if it is not already cached
- Not recommended for production (basic security checks only)

Use with this project:

```bash
export OPENAI_API_BASE=http://localhost:8080/v1
export OPENAI_MODEL=mlx-community/gemma-3n-E4B-it-lm-4bit
export OPENAI_API_KEY=mlx
python tia_portal_translator.py --service openai --source en-US --target de-DE
```

### Troubleshooting

- 404 on `/v1/chat/completions`: your base URL is  most likely missing `/v1`.
- Model not found: verify the model name in `OPENAI_MODEL`.

### References

- Ollama OpenAI compatibility: https://docs.ollama.com/api/openai-compatibility
- vLLM OpenAI-compatible server: https://docs.vllm.ai/en/v0.7.1/serving/openai_compatible_server.html
- MLX-LM server docs: https://raw.githubusercontent.com/ml-explore/mlx-lm/main/mlx_lm/SERVER.md

## Legacy

- Original legacy script: `deprecated/legacy/tia_portal_translator.py`

The modern CLI temporarily supports the legacy `--dest` flag. When `--dest` is
used with `--service google`, it maps to `google-free` for legacy behavior.

Legacy usage (unchanged):

```bash
python tia_portal_translator.py --service gpt --source en-US --dest de-DE
```

## License

This project is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).
