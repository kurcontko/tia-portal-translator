from __future__ import annotations

import asyncio
import sys
import types

import pytest

from tia_portal_translator.services.base import TranslationError, TranslationService
from tia_portal_translator.services.factory import TranslationServiceFactory
from tia_portal_translator.services.openai_service import OpenAITranslationService
from tia_portal_translator.services.google_free_service import GoogleTranslateFreeService
from tia_portal_translator.services.google_cloud_service import GoogleTranslationService
from tia_portal_translator.services.deepl_service import DeepLTranslationService


class DummyCache:
    def __init__(self, value: str | None = None) -> None:
        self.value = value
        self.set_calls: list[str] = []

    async def get(self, *_args, **_kwargs) -> str | None:
        return self.value

    async def set(self, text, *_args, **_kwargs) -> None:
        self.set_calls.append(text)


class DummyService(TranslationService):
    def __init__(self, *args, fail_times: int = 0, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fail_times = fail_times
        self.calls = 0

    async def translate(self, text: str) -> str:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("boom")
        return f"{text}-ok"


@pytest.mark.asyncio
async def test_translate_batch_skips_empty_and_returns_exceptions():
    service = DummyService(max_retries=1, request_delay=0)
    texts = ["hello", " ", "fail"]

    async def translate(text: str) -> str:
        if text == "fail":
            raise RuntimeError("nope")
        return f"{text}-ok"

    service.translate = translate  # type: ignore[assignment]
    results = await service.translate_batch(texts)
    assert results[0] == "hello-ok"
    assert results[1] == ""
    assert isinstance(results[2], TranslationError)


@pytest.mark.asyncio
async def test_translate_with_cache_hit_skips_translate():
    cache = DummyCache(value="cached")
    service = DummyService(cache=cache, request_delay=0)
    result = await service._translate_with_throttle("hello")
    assert result == "cached"
    assert service.calls == 0


@pytest.mark.asyncio
async def test_translate_with_cache_sets_on_success():
    cache = DummyCache(value=None)
    service = DummyService(cache=cache, request_delay=0)
    result = await service._translate_with_throttle("hello")
    assert result == "hello-ok"
    assert cache.set_calls == ["hello"]


@pytest.mark.asyncio
async def test_translate_retries_then_succeeds(monkeypatch):
    async def fast_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)
    service = DummyService(max_retries=3, fail_times=2, request_delay=0)
    result = await service._translate_with_throttle("hello")
    assert result == "hello-ok"
    assert service.calls == 3


@pytest.mark.asyncio
async def test_translate_retries_then_raises(monkeypatch):
    async def fast_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)
    service = DummyService(max_retries=2, fail_times=3, request_delay=0)
    with pytest.raises(TranslationError):
        await service._translate_with_throttle("hello")


def _install_openai_stub(monkeypatch):
    module = types.ModuleType("openai")

    class AsyncOpenAI:
        def __init__(self, api_key=None, base_url=None) -> None:
            self.api_key = api_key
            self.base_url = base_url
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=None),
            )

    class RateLimitError(Exception):
        pass

    class APIConnectionError(Exception):
        pass

    class APITimeoutError(Exception):
        pass

    module.AsyncOpenAI = AsyncOpenAI
    module.RateLimitError = RateLimitError
    module.APIConnectionError = APIConnectionError
    module.APITimeoutError = APITimeoutError
    monkeypatch.setitem(sys.modules, "openai", module)


@pytest.mark.asyncio
async def test_openai_translate_success(monkeypatch):
    _install_openai_stub(monkeypatch)
    service = OpenAITranslationService(api_key="key", request_delay=0)

    class Response:
        def __init__(self, content: str) -> None:
            self.choices = [types.SimpleNamespace(message=types.SimpleNamespace(content=content))]

    async def fake_create(_text: str):
        return Response(" hola ")

    service._create_completion = fake_create  # type: ignore[assignment]
    assert await service.translate("hello") == "hola"


@pytest.mark.asyncio
async def test_openai_translate_empty_content_raises(monkeypatch):
    _install_openai_stub(monkeypatch)
    service = OpenAITranslationService(api_key="key", request_delay=0)

    class Response:
        def __init__(self) -> None:
            self.choices = [types.SimpleNamespace(message=types.SimpleNamespace(content=""))]

    async def fake_create(_text: str):
        return Response()

    service._create_completion = fake_create  # type: ignore[assignment]
    with pytest.raises(TranslationError):
        await service.translate("hello")


@pytest.mark.asyncio
async def test_openai_translate_exception_wrapped(monkeypatch):
    _install_openai_stub(monkeypatch)
    service = OpenAITranslationService(api_key="key", request_delay=0)

    async def fake_create(_text: str):
        raise RuntimeError("boom")

    service._create_completion = fake_create  # type: ignore[assignment]
    with pytest.raises(TranslationError, match="OpenAI translation failed"):
        await service.translate("hello")


def _install_googletrans_stub(monkeypatch, translate_impl):
    module = types.ModuleType("googletrans")

    class Translator:
        def translate(self, text, dest):
            return translate_impl(text, dest)

    module.Translator = Translator
    monkeypatch.setitem(sys.modules, "googletrans", module)


@pytest.mark.asyncio
async def test_google_free_translate_success(monkeypatch):
    _install_googletrans_stub(
        monkeypatch,
        lambda text, dest: types.SimpleNamespace(text=f"{text}-{dest}"),
    )
    service = GoogleTranslateFreeService(target_language="de", request_delay=0)
    assert await service.translate("hello") == "hello-de"


@pytest.mark.asyncio
async def test_google_free_translate_error(monkeypatch):
    def raise_error(_text, _dest):
        raise RuntimeError("boom")

    _install_googletrans_stub(monkeypatch, raise_error)
    service = GoogleTranslateFreeService(target_language="de", request_delay=0)
    with pytest.raises(TranslationError, match="Google Translate \\(free\\) failed"):
        await service.translate("hello")


def _install_google_cloud_stub(monkeypatch, translate_impl):
    google_module = types.ModuleType("google")
    cloud_module = types.ModuleType("google.cloud")
    translate_module = types.ModuleType("google.cloud.translate_v2")

    class Client:
        def translate(self, text, target_language):
            return translate_impl(text, target_language)

    translate_module.Client = Client
    cloud_module.translate_v2 = translate_module
    google_module.cloud = cloud_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_module)
    monkeypatch.setitem(sys.modules, "google.cloud.translate_v2", translate_module)


@pytest.mark.asyncio
async def test_google_cloud_translate_success(monkeypatch):
    _install_google_cloud_stub(
        monkeypatch,
        lambda text, target_language: {"translatedText": f"{text}-{target_language}"},
    )
    service = GoogleTranslationService(target_language="de", request_delay=0)
    assert await service.translate("hello") == "hello-de"


@pytest.mark.asyncio
async def test_google_cloud_translate_error(monkeypatch):
    def raise_error(_text, _target_language):
        raise RuntimeError("boom")

    _install_google_cloud_stub(monkeypatch, raise_error)
    service = GoogleTranslationService(target_language="de", request_delay=0)
    with pytest.raises(TranslationError, match="Google translation failed"):
        await service.translate("hello")


def _install_deepl_stub(monkeypatch, translate_impl):
    module = types.ModuleType("deepl")

    class Translator:
        def __init__(self, _api_key):
            pass

        def translate_text(self, text, target_lang):
            return translate_impl(text, target_lang)

    module.Translator = Translator
    monkeypatch.setitem(sys.modules, "deepl", module)


@pytest.mark.asyncio
async def test_deepl_translate_success(monkeypatch):
    class Result:
        def __init__(self, value: str) -> None:
            self.value = value

        def __str__(self) -> str:
            return self.value

    _install_deepl_stub(monkeypatch, lambda text, target_lang: Result(f"{text}-{target_lang}"))
    service = DeepLTranslationService(api_key="key", target_language="EN", request_delay=0)
    assert await service.translate("hello") == "hello-EN"


@pytest.mark.asyncio
async def test_deepl_translate_error(monkeypatch):
    def raise_error(_text, _target_lang):
        raise RuntimeError("boom")

    _install_deepl_stub(monkeypatch, raise_error)
    service = DeepLTranslationService(api_key="key", target_language="EN", request_delay=0)
    with pytest.raises(TranslationError, match="DeepL translation failed"):
        await service.translate("hello")


def test_translation_service_factory_invalid():
    with pytest.raises(ValueError, match="Unsupported service"):
        TranslationServiceFactory.create_service("unknown")


def test_translation_service_factory_gpt(monkeypatch):
    _install_openai_stub(monkeypatch)
    service = TranslationServiceFactory.create_service("gpt", api_key="key", target_language="de")
    assert isinstance(service, OpenAITranslationService)
