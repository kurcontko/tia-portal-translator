from googletrans import Translator  # use 3.1.0a0 

from services import TranslationService


class GoogleTranslationService(TranslationService):
    def translate(self, text, destination_language, source_language='auto'):
        translator = Translator()
        return translator.translate(text, dest=destination_language, src=source_language).text
    
    def translate_batch(self, texts, destination_language, source_language='auto'):
        translator = Translator()
        return translator.translate(texts, dest=destination_language, src=source_language)