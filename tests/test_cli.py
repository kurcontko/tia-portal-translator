import asyncio
import sys
import types

import pytest

import tia_portal_translator.cli as cli


def test_parse_arguments_with_dest(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--service", "google", "--source", "en-US", "--dest", "de-DE"],
    )
    args = cli.parse_arguments()
    assert args.dest == "de-DE"
    assert args.target is None


@pytest.mark.asyncio
async def test_main_uses_dest_alias_and_cache_stats(monkeypatch):
    calls: dict[str, object] = {}

    class DummyCache:
        def __init__(self) -> None:
            self.cleared = False

        async def clear(self) -> None:
            self.cleared = True

        async def get_stats(self) -> dict[str, str]:
            return {"type": "dummy"}

    dummy_cache = DummyCache()

    class DummyCacheFactory:
        @staticmethod
        def create_cache(*_args, **kwargs):
            calls["cache_kwargs"] = kwargs
            return dummy_cache

    class DummyCacheManager:
        def __init__(self, cache):
            calls["cache_manager"] = cache

        async def print_stats(self) -> None:
            calls["stats"] = True

    class DummyPipeline:
        def __init__(self, config, service, run_id=None) -> None:
            calls["config"] = config
            calls["service"] = service
            calls["run_id"] = run_id

        async def translate_project(self, source, target) -> None:
            calls["translate"] = (source, target)

    def dummy_create_service(service_name, target_language, cache, **_kwargs):
        calls["service_name"] = service_name
        calls["target_language"] = target_language
        calls["cache"] = cache
        return object()

    monkeypatch.setattr(cli, "CacheFactory", DummyCacheFactory)
    monkeypatch.setattr(cli, "CacheManager", DummyCacheManager)
    monkeypatch.setattr(cli, "TranslatorPipeline", DummyPipeline)
    monkeypatch.setattr(cli.TranslationServiceFactory, "create_service", dummy_create_service)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--service",
            "google",
            "--source",
            "en-US",
            "--dest",
            "de-DE",
            "--cache-stats",
            "--clear-cache",
        ],
    )

    await cli.main()

    assert calls["service_name"] == "google-free"
    assert calls["translate"] == ("en-US", "de-DE")
    assert calls["cache"] is dummy_cache
    assert dummy_cache.cleared is True
    assert calls["stats"] is True


@pytest.mark.asyncio
async def test_main_raises_without_target(monkeypatch):
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--service", "google-free", "--source", "en-US"],
    )
    with pytest.raises(ValueError, match="Missing required --target"):
        await cli.main()


@pytest.mark.asyncio
async def test_main_rejects_mismatched_dest_and_target(monkeypatch):
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
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
            "--dest",
            "fr-FR",
        ],
    )
    with pytest.raises(ValueError, match="Specify only one of --dest or --target"):
        await cli.main()


@pytest.mark.asyncio
async def test_main_skips_cache_when_disabled(monkeypatch):
    def fail_create_cache(*_args, **_kwargs):
        raise AssertionError("cache creation should be skipped")

    class DummyPipeline:
        def __init__(self, config, service, run_id=None) -> None:
            pass

        async def translate_project(self, source, target) -> None:
            return None

    monkeypatch.setattr(cli, "CacheFactory", types.SimpleNamespace(create_cache=fail_create_cache))
    monkeypatch.setattr(cli, "TranslatorPipeline", DummyPipeline)
    monkeypatch.setattr(cli.TranslationServiceFactory, "create_service", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)

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
            "--cache-type",
            "none",
        ],
    )
    await cli.main()


def test_main_module_invokes_asyncio_run(monkeypatch):
    import runpy

    async def dummy_main():
        return "ok"

    captured: dict[str, object] = {}

    def fake_run(coro):
        captured["coro"] = coro
        coro.close()

    monkeypatch.setattr(cli, "main", dummy_main)
    monkeypatch.setattr(asyncio, "run", fake_run)

    runpy.run_module("tia_portal_translator.__main__", run_name="__main__")
    assert "coro" in captured
