import openai

from services.base import TranslationService


class GPTTranslationService(TranslationService):
    def translate(self, text):
        openai.api_key = self.api_key
        prompt = f'Translate the following text to "{self.destination_language}" language:\n{text}'
        response = openai.Completion.create(
            engine='text-davinci-002',
            prompt=prompt,
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.5,
        )
        return response.choices[0].text.strip()

