from tia_portal_translator.cache import CacheFactory, TranslationCache
from tia_portal_translator.cache.base import TranslationCache as BaseTranslationCache
from tia_portal_translator.cache.factory import CacheFactory as FactoryImpl


def test_cache_exports():
    assert CacheFactory is FactoryImpl
    assert TranslationCache is BaseTranslationCache
