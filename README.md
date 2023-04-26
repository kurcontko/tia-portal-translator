# TIA Portal Translator
Translation tool for TIA Portal texts exported to Excel using Google Translate, GPT, and DeepL APIs.

## Getting Started

### Prerequisites

Before you start using this script, make sure you have the following installed:

* Python: This script requires Python 3.6 or higher. You can download the latest version of Python from the official website.

* Googletrans: This script uses the Googletrans library:

```
pip install googletrans
```
* Openpyxl: This script also requires the Openpyxl library to work with Excel files:

```
pip install openpyxl
```
* OpenAI: If you want to use GPT for translations, you will need the OpenAI library:

```
pip install openai
```
* DeepL: If you want to use DeepL for translations, you will need the DeepL library:

```
pip install deepl
```

Make sure to also have API keys for the translation services you want to use (GPT, DeepL) and set them as environment variables.

## Usage

You will need to run the script with the --service flag, specifying which translation service you want to use. 

1. For Google Translate:

```
python tia_portal_translator.py --service google
```

2. For ChatGPT:

```
python tia_portal_translator.py --service gpt
```

3. For DeepL:

```
python tia_portal_translator.py --service deepl
```

## License

This project is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).
