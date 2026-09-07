from __future__ import annotations

import argparse
import json

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        """Allow diagnostics before optional runtime dependencies are installed."""
        return False

from .config import ConfigurationError, Settings
from .engine import ResearchEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ResearchMind research assistant")
    parser.add_argument("query", nargs="?", help="Research question or writing task")
    parser.add_argument(
        "--diagnose", action="store_true", help="Validate the installation without an API call"
    )
    return parser


def main() -> int:
    load_dotenv()
    args = build_parser().parse_args()
    try:
        settings = Settings.from_env(require_api_key=not args.diagnose)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}")
        return 2

    engine = ResearchEngine(settings)
    if args.diagnose:
        print(json.dumps(engine.health(), indent=2))
        return 0
    if not args.query:
        print("Provide a research query or use --diagnose.")
        return 2

    print(json.dumps(engine.run(args.query).to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
