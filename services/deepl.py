from deepl import DeepLTranslator

from services.base import TranslationService


class DeepLTranslationService(TranslationService):
    def translate(self, text):
        translator = DeepLTranslator(self.api_key)
        return translator.translate_text(text, target_lang=self.destination_language)
