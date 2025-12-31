from pathlib import Path

import tia_portal_translator.config as config_module
from tia_portal_translator.config import Config


def test_config_sets_default_paths(monkeypatch):
    monkeypatch.setattr(
        config_module,
        "user_cache_dir",
        lambda *_args, **_kwargs: "/tmp/tia-cache",
    )

    config = Config(excel_file="input.xlsx", output_file=None, cache_db_path="", cache_dir="")

    assert config.output_file == "input_translated.xlsx"
    assert config.cache_db_path == str(Path("/tmp/tia-cache") / "translation_cache.db")
    assert config.cache_dir == str(Path("/tmp/tia-cache") / "translation_cache")
