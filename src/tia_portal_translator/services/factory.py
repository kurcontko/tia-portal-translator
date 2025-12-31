from typing import Optional

from tia_portal_translator.cache import TranslationCache
from tia_portal_translator.services.base import TranslationService
from tia_portal_translator.services.deepl_service import DeepLTranslationService
from tia_portal_translator.services.google_cloud_service import GoogleTranslationService
from tia_portal_translator.services.google_free_service import GoogleTranslateFreeService
from tia_portal_translator.services.openai_service import OpenAITranslationService


class TranslationServiceFactory:
    """Factory for creating translation services."""

    @staticmethod
    def create_service(
        service_name: str,
        api_key: Optional[str] = None,
        source_language: str = "auto",
        target_language: str = "en",
        cache: Optional[TranslationCache] = None,
        max_concurrent_requests: int = 10,
        request_delay: float = 0.1,
        max_retries: int = 3,
    ) -> TranslationService:
        services: dict[str, type[TranslationService]] = {
            "openai": OpenAITranslationService,
            "gpt": OpenAITranslationService,  # Alias for backward compatibility
            "deepl": DeepLTranslationService,
            "google": GoogleTranslationService,
            "google-free": GoogleTranslateFreeService,
        }

        key = service_name.lower()
        if key not in services:
            raise ValueError(
                f"Unsupported service: {service_name}. "
                f"Available services: {list(services.keys())}"
            )

        service: TranslationService = services[key](
            api_key,
            source_language,
            target_language,
            cache,
            max_concurrent_requests=max_concurrent_requests,
            request_delay=request_delay,
            max_retries=max_retries,
        )
        return service
