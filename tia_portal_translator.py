#!/usr/bin/env python3
"""
CLI entrypoint for running the TIA Portal Translator without module install.
"""

import asyncio

from tia_portal_translator.cli import main as cli_main


def main() -> None:
    asyncio.run(cli_main())


if __name__ == "__main__":
    main()
