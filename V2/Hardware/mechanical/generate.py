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
V2_DIR = MECHANICAL_DIR.parents[1]
CODE_DIR = V2_DIR / "Code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from physical_variants import PhysicalVariant, PhysicalVariantError, load_variant


def _profile_path(variant_id: str) -> Path:
    return (
        V2_DIR / ("Prototype" if variant_id == "prototype" else "Final") / "design.toml"
    )


def _validate_profile(variant: PhysicalVariant, params) -> None:
    """Refuse to generate a physical package with mixed variant dimensions."""

    expected = {
        "card.body_width": (params.card.body_width, variant.card.body_width_mm),
        "card.total_height": (params.card.total_height, variant.card.total_height_mm),
        "card.tab_width": (params.card.tab_width, variant.card.tab_width_mm),
        "card.tab_height": (params.card.tab_height, variant.card.tab_height_mm),
        "card.sticker_width": (params.card.sticker_width, variant.sticker.width_mm),
        "card.sticker_face_height": (
            params.card.sticker_face_height,
            variant.sticker.split_y_mm,
        ),
        "drum.positions": (params.drum.positions, variant.drum.positions),
        "drum.diameter": (params.drum.diameter, variant.drum.diameter_mm),
        "drum.inner_width": (params.drum_inner_width, variant.drum.inner_width_mm),
        "drum.outer_width": (params.drum_outer_width, variant.drum.outer_width_mm),
    }
    mismatches = [
        f"{name}: profile={actual:g}, variant={wanted:g}"
        for name, (actual, wanted) in expected.items()
        if round(actual, 6) != round(wanted, 6)
    ]
    if mismatches:
        raise PhysicalVariantError(
            f"{variant.name} profile mismatch: " + "; ".join(mismatches)
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=V2_DIR / "Final/generated/mechanical",
    )
    parser.add_argument(
        "--variant",
        choices=("prototype", "definitive"),
        default="definitive",
        help="isolated physical V2 package to generate",
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
    profile_path = args.profile or _profile_path(variant.id)
    params = load_design_profile(profile_path, base=DESIGN)
    try:
        _validate_profile(variant, params)
    except PhysicalVariantError as error:
        parser.error(str(error))
    generate(args.output, params=params, physical_variant=variant.id)


if __name__ == "__main__":
    main()
