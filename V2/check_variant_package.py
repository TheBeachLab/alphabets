#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Validate that one V2 folder is a complete, unmixed physical package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

V2_DIR = Path(__file__).resolve().parent
CODE_DIR = V2_DIR / "Code"
MECHANICAL_DIR = V2_DIR / "Hardware" / "mechanical"
for source in (CODE_DIR, MECHANICAL_DIR):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))

from alphabets_cad.parameters import DESIGN, load_design_profile
from json_license_metadata import validate_json_license
from physical_variants import load_variant


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_json_license(data, str(path))
    return data


def equal(actual: float, expected: float, label: str) -> None:
    if round(float(actual), 6) != round(float(expected), 6):
        raise RuntimeError(f"{label}: expected {expected:g}, got {actual:g}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("prototype", "definitive"), required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    variant = load_variant(args.variant)
    params = load_design_profile(root / "design.toml", base=DESIGN)
    equal(params.card.body_width, variant.card.body_width_mm, "card body width")
    equal(params.card.total_height, variant.card.total_height_mm, "card height")
    equal(params.card.sticker_width, variant.sticker.width_mm, "sticker width")
    equal(
        params.card.sticker_face_height,
        variant.sticker.split_y_mm,
        "sticker split",
    )
    equal(params.drum_inner_width, variant.drum.inner_width_mm, "drum inner width")
    equal(params.drum_outer_width, variant.drum.outer_width_mm, "drum outer width")

    card_manifest = load_json(
        root
        / "generated"
        / "cards"
        / f"card-{variant.card.body_width_mm:g}x{variant.card.total_height_mm:g}.json"
    )
    if card_manifest["physical_variant"] != variant.id:
        raise RuntimeError("card manifest belongs to another physical variant")

    for sticker_path in variant.artifacts["sticker_outputs"]:
        sticker_manifest = load_json(
            V2_DIR.parent / Path(sticker_path).with_suffix(".json")
        )
        if sticker_manifest["physical_variant"] != variant.id:
            raise RuntimeError(f"mixed sticker output: {sticker_path}")

    mechanical = load_json(root / "generated" / "mechanical" / "manifest.json")
    equal(
        mechanical["parameters"]["drum"]["outer_width"],
        variant.drum.outer_width_mm,
        "mechanical drum outer width",
    )

    scene = load_json(root / "generated" / "blender" / "scene.json")
    capture = load_json(root / "generated" / "blender" / "cards-position-capture.json")
    enclosure = load_json(root / "generated" / "enclosure" / "manifest.json")
    for label, data in (
        ("scene", scene),
        ("capture", capture),
        ("enclosure", enclosure),
    ):
        if data.get("physical_variant") != variant.id:
            raise RuntimeError(f"{label} belongs to another physical variant")

    inner_width = (
        enclosure["limits_mm"]["inner_x_max"] - enclosure["limits_mm"]["inner_x_min"]
    )
    minimum_card_width = (
        params.card.overall_width + 2 * params.drum_enclosure.axial_clearance
    )
    if inner_width < minimum_card_width:
        raise RuntimeError(
            f"enclosure cavity {inner_width:g} mm is narrower than the card envelope "
            f"requirement {minimum_card_width:g} mm"
        )
    support_gap = (
        params.drum_outer_width
        + params.drum_enclosure.motor_mount_disc_clearance
        + params.drum_enclosure.shaft_support_axial_clearance
    )
    if support_gap < variant.drum.outer_width_mm:
        raise RuntimeError("enclosure supports are narrower than the selected drum")

    expected_pawl = f"pawl_{variant.id}"
    plate_parts = set(enclosure["print_plate"]["parts"])
    if plate_parts != {"enclosure_upper", "enclosure_lower", expected_pawl}:
        raise RuntimeError(f"print plate contains mixed parts: {sorted(plate_parts)}")

    required = [
        root
        / "generated"
        / "blender"
        / f"alphabets-v2-{'prototype' if variant.id == 'prototype' else 'final'}.blend",
        root / "generated" / "enclosure" / "print" / "captured-enclosure-upper.stl",
        root / "generated" / "enclosure" / "print" / "captured-enclosure-lower.stl",
        root / "generated" / "enclosure" / "print" / "captured-enclosure-pawl.stl",
        root
        / "generated"
        / "enclosure"
        / "print"
        / "captured-enclosure-print-plate.stl",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("missing package artifacts: " + ", ".join(missing))

    result = {
        "variant": variant.id,
        "card_body_mm": [params.card.body_width, params.card.total_height],
        "sticker_mm": [params.card.sticker_width, 2 * params.card.sticker_face_height],
        "drum_outer_width_mm": params.drum_outer_width,
        "enclosure_inner_width_mm": round(inner_width, 6),
        "support_gap_mm": round(support_gap, 6),
        "tab_radial_clearance_mm": round(params.flap_tab_radial_clearance, 6),
        "status": "internally consistent; physical fabrication not validated",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
