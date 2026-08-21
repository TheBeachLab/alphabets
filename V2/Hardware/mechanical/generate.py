#!/usr/bin/env python3
"""Generate every manufacturing and review artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alphabets_cad.export import generate

MECHANICAL_DIR = Path(__file__).resolve().parent
V2_DIR = MECHANICAL_DIR.parents[1]
CODE_DIR = V2_DIR / "Code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from physical_variants import PhysicalVariantError, load_variant


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "generated",
    )
    parser.add_argument(
        "--variant",
        choices=("prototype", "definitive"),
        default="definitive",
        help="physical V2 variant; only Definitivo has a current enclosure source",
    )
    args = parser.parse_args()
    try:
        variant = load_variant(args.variant)
    except PhysicalVariantError as error:
        parser.error(str(error))
    if variant.enclosure.status != "manufacturing-source":
        parser.error(
            f"{variant.name} has no validated enclosure generator; use its historical "
            f"reference at {variant.enclosure.source}"
        )
    generate(args.output)


if __name__ == "__main__":
    main()
