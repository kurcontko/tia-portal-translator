# TIA Portal Translator
Translation tool for TIA Portal texts exported to Excel using Google Translate, GPT, and DeepL APIs.

## Getting Started

### Prerequisites

Before you start using this script, make sure you have the following installed:

* Python: This script requires Python 3.6 or higher. You can download the latest version of Python from the official website.

* Openpyxl: This script also requires the Openpyxl library to work with Excel files:

```
pip install openpyxl
```

* Googletrans: If you want to use Google for translations (please use version 3.1.0a0):

```
pip install googletrans==3.1.0a0
```

* OpenAI: If you want to use GPT for translations:

```
pip install openai
```
* DeepL: If you want to use DeepL for translations:

```
pip install deepl
```

Make sure to also have API keys for the translation services you want to use (GPT, DeepL) and set them as environment variables.

## Usage

You will need to run the script with the --service flag, specifying which translation service you want to use, as well as with --source and --dest language and region arguments. 
Here's an example usage for translating from English (United States) to German using Google Translate or GPT:

```
python tia_portal_translator.py --service google --source en-US --dest de-DE
```

```
python tia_portal_translator.py --service gpt --source en-US --dest de-DE
```

## License

This project is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).
