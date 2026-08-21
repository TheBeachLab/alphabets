#!/usr/bin/env python3
"""Generate every manufacturing and review artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from alphabets_cad.export import generate
from alphabets_cad.parameters import DESIGN, load_design_profile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "generated",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        help="TOML profile with direct-dimension overrides",
    )
    args = parser.parse_args()
    params = load_design_profile(args.profile, base=DESIGN) if args.profile else DESIGN
    generate(args.output, params=params)


if __name__ == "__main__":
    main()
