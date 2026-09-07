"""Compatibility launcher for environments expecting App.py."""

from researchmind.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
