#!/usr/bin/env python3
"""Generate every manufacturing and review artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from alphabets_cad.export import generate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "generated",
    )
    args = parser.parse_args()
    generate(args.output)


if __name__ == "__main__":
    main()
