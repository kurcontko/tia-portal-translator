import argparse
import asyncio
import logging
from typing import Optional, Union
from uuid import uuid4

from dotenv import load_dotenv

from tia_portal_translator.cache import CacheFactory, CacheManager
from tia_portal_translator.config import Config
from tia_portal_translator.pipeline import TranslatorPipeline
from tia_portal_translator.services import TranslationServiceFactory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _format_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _log_context(run_id: str, chunk_id: Optional[Union[int, str]] = None) -> str:
    chunk_value = "-" if chunk_id is None else chunk_id
    return f"run_id={run_id} chunk_id={chunk_value}"


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Modern TIA Portal Translator with async support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tia_portal_translator.py --service openai --source en-US --target de-DE
  python tia_portal_translator.py --service deepl --source en-US --target fr-FR
  python tia_portal_translator.py --service google --source de-DE --target en-US --file custom.xlsx
  python tia_portal_translator.py --service google-free --source en-US --target de-DE  # Free, no API key
  python tia_portal_translator.py --service google --source en-US --dest de-DE  # Legacy alias
        """,
    )

    parser.add_argument(
        "--service",
        choices=["openai", "gpt", "deepl", "google", "google-free"],
        required=True,
        help="Translation service to use (google-free requires no API key)",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Source language and region (e.g., en-US, fr-FR, de-DE)",
    )
    parser.add_argument(
        "--target",
        help="Target language and region (e.g., en-US, fr-FR, de-DE)",
    )
    parser.add_argument("--dest", help="Legacy alias for --target")
    parser.add_argument(
        "--file",
        default="TIAProjectTexts.xlsx",
        help="Input Excel file path (default: TIAProjectTexts.xlsx)",
    )
    parser.add_argument(
        "--output",
        help="Output Excel file path (default: auto-generated)",
    )
    parser.add_argument(
        "--sheet",
        default="User Texts",
        help="Excel sheet name (default: User Texts)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100,
        help="Number of texts to process in each chunk (default: 100)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum concurrent translation requests (default: 10)",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.1,
        help="Delay between translation requests in seconds (default: 0.1)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries per request (default: 3)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--preserve-line-lengths",
        action="store_true",
        help="Preserve similar line lengths as source text (useful for UI text with fixed display widths)",
    )
    parser.add_argument(
        "--line-length-tolerance",
        type=float,
        default=1.2,
        help="Line length tolerance multiplier (default: 1.2 = 20%% longer allowed)",
    )
    parser.add_argument(
        "--skip-formulas",
        action="store_true",
        help="Skip formula cells in the source column",
    )

    parser.add_argument(
        "--cache-type",
        choices=["memory", "sqlite", "file", "hybrid", "none"],
        default="hybrid",
        help="Type of cache to use (default: hybrid)",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=24 * 7,  # 1 week
        help="Cache TTL in hours (default: 168 = 1 week)",
    )
    parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="Show cache statistics after translation",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before starting translation",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort translation on the first error",
    )
    parser.add_argument(
        "--report",
        help="Write a translation report to a .json or .csv file",
    )

    return parser.parse_args()


async def main() -> None:
    """Main entry point."""
    load_dotenv()
    args = parse_arguments()
    run_id = uuid4().hex[:12]

    if args.dest and args.target and args.dest != args.target:
        raise ValueError("Specify only one of --dest or --target.")
    if not args.target:
        if args.dest:
            args.target = args.dest
            logger.warning("%s event=legacy_dest_used", _log_context(run_id))
            if args.service == "google":
                args.service = "google-free"
                logger.warning(
                    "%s event=legacy_service_mapped from=google to=google-free",
                    _log_context(run_id),
                )
        else:
            raise ValueError("Missing required --target (or legacy --dest).")

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = Config(
        excel_file=args.file,
        sheet_name=args.sheet,
        output_file=args.output,
        chunk_size=args.chunk_size,
        max_concurrent_requests=args.max_concurrent,
        request_delay=args.request_delay,
        max_retries=args.max_retries,
        preserve_line_lengths=args.preserve_line_lengths,
        line_length_tolerance=args.line_length_tolerance,
        cache_enabled=args.cache_type != "none",
        cache_type=args.cache_type,
        cache_ttl_hours=args.cache_ttl,
        fail_fast=args.fail_fast,
        report_path=args.report,
        skip_formulas=args.skip_formulas,
    )

    target_language_code = args.target.split("-")[0]

    try:
        cache = None
        if config.cache_enabled:
            cache = CacheFactory.create_cache(
                config.cache_type,
                ttl_hours=config.cache_ttl_hours,
                memory_size=config.cache_max_memory_size,
                db_path=config.cache_db_path,
                cache_dir=config.cache_dir,
            )
            logger.info(
                "%s event=cache_init cache_type=%s cache_ttl_hours=%s",
                _log_context(run_id),
                config.cache_type,
                config.cache_ttl_hours,
            )

            if args.clear_cache:
                await cache.clear()
                logger.info("%s event=cache_cleared", _log_context(run_id))

        translation_service = TranslationServiceFactory.create_service(
            args.service,
            source_language=args.source,
            target_language=target_language_code,
            cache=cache,
            max_concurrent_requests=config.max_concurrent_requests,
            request_delay=config.request_delay,
            max_retries=config.max_retries,
        )

        translator = TranslatorPipeline(config, translation_service, run_id=run_id)
        await translator.translate_project(args.source, args.target)

        if cache and args.cache_stats:
            cache_manager = CacheManager(cache)
            await cache_manager.print_stats()

    except Exception as exc:
        logger.error("%s event=run_failed error=%s", _log_context(run_id), _format_error(exc))
        raise


if __name__ == "__main__":
    asyncio.run(main())
