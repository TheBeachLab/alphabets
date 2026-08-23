#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Generate every manufacturing and review artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alphabets_cad.export import generate
from alphabets_cad.parameters import DESIGN, load_design_profile

MECHANICAL_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = MECHANICAL_DIR.parents[3]
VARIANTS_DIR = REPOSITORY_ROOT / "V2/Hardware/variants"
if str(VARIANTS_DIR) not in sys.path:
    sys.path.insert(0, str(VARIANTS_DIR))

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
    parser.add_argument(
        "--profile",
        type=Path,
        help="TOML profile with direct-dimension overrides",
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
    params = load_design_profile(args.profile, base=DESIGN) if args.profile else DESIGN
    generate(args.output, params=params)


if __name__ == "__main__":
    main()
