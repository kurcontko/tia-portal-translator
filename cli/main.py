# cli/main.py
import argparse
from ..core.translator import translate_excel

def parse_arguments():
    parser = argparse.ArgumentParser(description='Translate an Excel file using Google Translate, GPT, or DeepL.')
    parser.add_argument('--service', choices=['google', 'gpt', 'deepl'], required=True, help='Choose the translation service (google, gpt, or deepl).')
    parser.add_argument('--source', required=True, help='Source language and region (e.g., en-US, fr-FR, de-DE).')
    parser.add_argument('--dest', required=True, help='Destination language and region (e.g., en-US, fr-FR, de-DE).')
    parser.add_argument('--file', required=True, help='Path to the Excel file.')
    parser.add_argument('--sheet', required=True, help='Excel sheet name.')
    args = parser.parse_args()
    return args

def main():
    args = parse_arguments()
    translate_excel(args.service, args.source, args.dest, args.file, args.sheet)

if __name__ == '__main__':
    main()