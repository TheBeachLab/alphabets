#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Prepare exact CAD references and metadata for the HALLO/WELT! scene."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BLENDER_DIR = Path(__file__).resolve().parent
V2_DIR = BLENDER_DIR.parents[1]
MECHANICAL_DIR = V2_DIR / "Hardware/mechanical"
FINAL_DIR = V2_DIR / "Final"
OUTPUT_DIR = FINAL_DIR / "generated/blender/hello-wall"
CODE_DIR = V2_DIR / "Code"
COMPONENTS_DIR = OUTPUT_DIR / "components"
CAPTURE_PATH = FINAL_DIR / "generated/blender/cards-position-capture.json"
ENCLOSURE_MANIFEST_PATH = FINAL_DIR / "generated/enclosure/manifest.json"
STICKER_MAPPING_PATH = FINAL_DIR / "generated/blender/sticker-mapping.json"
FONT_PATH = V2_DIR / "Hardware/stickers/fonts/BlueHighwayD-International.otf"
ROWS = ("HALLO", "WELT!")
BACKGROUND_RGB = (2, 3, 4)
LETTER_RGB = (255, 204, 0)
MOTOR_COMPONENTS = ("motor_body", "motor_collar", "motor_backpack", "motor_shaft")

if str(MECHANICAL_DIR) not in sys.path:
    sys.path.insert(0, str(MECHANICAL_DIR))
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from alphabets_cad.assemblies import captured_enclosure_design_components
from alphabets_cad.parameters import DESIGN
from json_license_metadata import validate_json_license, write_licensed_json


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_json_license(data, str(path))
    return data


def _round_vector(*values: float) -> list[float]:
    return [round(value, 9) for value in values]


def _character_uv(character: str) -> dict[str, dict[str, object]]:
    assignments = load_json(STICKER_MAPPING_PATH)["assignments"]
    matches = [item for item in assignments if item["character"] == character]
    if len(matches) != 2:
        raise RuntimeError(f"expected two production-atlas halves for {character!r}")
    return {
        item["display_half"]: {
            "uv_box": item["uv_box"],
            "rotation_degrees": item["rotation_degrees"],
            "horizontal_flip": item["horizontal_flip"],
            "character_index": item["character_index"],
        }
        for item in matches
    }


def _fastener_layout(
    limits: dict[str, float], enclosure: dict[str, float], capture: dict[str, Any]
) -> list[dict[str, object]]:
    front_y = limits["front_y"]
    outer_x_min = limits["outer_x_min"]
    recessed_motor_face_x = outer_x_min + enclosure["motor_inset_depth"]
    pawl_bounds = capture["pawl"]["bounds_world_mm"]
    pawl_thickness = (
        float(pawl_bounds["maximum"][1])
        - float(pawl_bounds["minimum"][1])
        + enclosure["pawl_thickness_addition"]
    )
    pawl_outer_y = front_y + pawl_thickness
    pawl_axis_z = (limits["inner_top_z"] + limits["outer_top_z"]) / 2
    pawl_head_depth = enclosure["pawl_head_recess_depth"]
    pawl_shaft_outer = pawl_outer_y - pawl_head_depth
    pawl_shaft_inner = front_y - enclosure["pawl_pilot_depth"]

    shaft_recess_face_x = limits["outer_x_max"] - enclosure["docking_recess_depth"]
    shaft_head_depth = enclosure["shaft_head_recess_depth"]
    shaft_outer = shaft_recess_face_x - shaft_head_depth
    shaft_inner = DESIGN.drum_outer_width / 2 - DESIGN.drum.side_thickness

    motor_bracket_outer_x = recessed_motor_face_x - DESIGN.motor.mount_bracket_height
    motor_head_depth = 2.0
    motor_shaft_inner = (
        -DESIGN.drum_outer_width / 2 - enclosure["motor_mount_disc_clearance"]
    )

    def screw(
        name: str,
        axis: str,
        head_diameter: float,
        head_depth: float,
        head_center: tuple[float, float, float],
        slot_center: tuple[float, float, float],
        shaft_start: tuple[float, float, float],
        shaft_end: tuple[float, float, float],
    ) -> dict[str, object]:
        axis_index = {"X": 0, "Y": 1, "Z": 2}[axis]
        shaft_depth = abs(shaft_end[axis_index] - shaft_start[axis_index])
        shaft_center = tuple(
            (shaft_start[index] + shaft_end[index]) / 2 for index in range(3)
        )
        return {
            "name": name,
            "axis": axis,
            "nominal": "M3",
            "head_diameter_mm": head_diameter,
            "head_depth_mm": head_depth,
            "head_center_mm": _round_vector(*head_center),
            "slot_center_mm": _round_vector(*slot_center),
            "shaft_diameter_mm": 3.0,
            "shaft_depth_mm": round(shaft_depth, 9),
            "shaft_center_mm": _round_vector(*shaft_center),
        }

    fasteners = [
        screw(
            "pawl",
            "Y",
            enclosure["pawl_head_recess_diameter"],
            pawl_head_depth,
            (0, pawl_outer_y - pawl_head_depth / 2, pawl_axis_z),
            (0, pawl_outer_y + 0.01, pawl_axis_z),
            (0, pawl_shaft_outer, pawl_axis_z),
            (0, pawl_shaft_inner, pawl_axis_z),
        ),
        screw(
            "axle",
            "X",
            enclosure["shaft_head_recess_diameter"],
            shaft_head_depth,
            (shaft_recess_face_x - shaft_head_depth / 2, 0, 0),
            (shaft_recess_face_x + 0.01, 0, 0),
            (shaft_outer, 0, 0),
            (shaft_inner, 0, 0),
        ),
    ]
    for side, mount_y in (
        ("negative_y", -DESIGN.motor.mount_center_offset),
        ("positive_y", DESIGN.motor.mount_center_offset),
    ):
        fasteners.append(
            screw(
                f"motor_{side}",
                "X",
                6.2,
                motor_head_depth,
                (
                    motor_bracket_outer_x - motor_head_depth / 2,
                    mount_y,
                    -DESIGN.motor.shaft_offset,
                ),
                (
                    motor_bracket_outer_x - motor_head_depth - 0.01,
                    mount_y,
                    -DESIGN.motor.shaft_offset,
                ),
                (
                    motor_bracket_outer_x,
                    mount_y,
                    -DESIGN.motor.shaft_offset,
                ),
                (
                    motor_shaft_inner,
                    mount_y,
                    -DESIGN.motor.shaft_offset,
                ),
            )
        )
    return fasteners


def _magnet_layout(
    limits: dict[str, float], enclosure: dict[str, float]
) -> list[dict[str, object]]:
    center_y = (limits["back_y"] + limits["front_y"]) / 2
    x_centers = (
        (limits["outer_x_min"] + limits["inner_x_min"]) / 2,
        (limits["outer_x_max"] + limits["inner_x_max"]) / 2,
    )
    split_height = enclosure["capture_split_height"]
    split_gap = enclosure["split_gap"]
    thickness = enclosure["magnet_thickness"]
    magnets = []
    for side, x in (("left", x_centers[0]), ("right", x_centers[1])):
        magnets.extend(
            (
                {
                    "name": f"split_upper_{side}",
                    "center_mm": _round_vector(
                        x, center_y, split_height + split_gap / 2 + thickness / 2
                    ),
                },
                {
                    "name": f"split_lower_{side}",
                    "center_mm": _round_vector(
                        x, center_y, split_height - split_gap / 2 - thickness / 2
                    ),
                },
            )
        )
    magnets.extend(
        (
            {
                "name": "stack_top_alpha",
                "center_mm": _round_vector(
                    0, center_y, limits["outer_top_z"] - thickness / 2
                ),
            },
            {
                "name": "stack_bottom",
                "center_mm": _round_vector(
                    0, center_y, limits["outer_bottom_z"] + thickness / 2
                ),
            },
        )
    )
    return magnets


def build_manifest() -> dict[str, object]:
    enclosure_manifest = load_json(ENCLOSURE_MANIFEST_PATH)
    capture = load_json(CAPTURE_PATH)
    limits = enclosure_manifest["limits_mm"]
    enclosure = enclosure_manifest["parameters"]
    modules = []
    for row_index, row in enumerate(ROWS, start=1):
        for column_index, character in enumerate(row, start=1):
            modules.append(
                {
                    "row": row_index,
                    "column": column_index,
                    "character": character,
                    "production_atlas_uv": _character_uv(character),
                }
            )
    return {
        "schema_version": 2,
        "title": "German hello world",
        "spoken_message": "HALLO WELT!",
        "display_rows": list(ROWS),
        "layout": {"rows": 2, "columns": 5, "module_count": 10},
        "electronics_included": False,
        "motor_included": True,
        "scene_kind": "technical assembly; no render generated",
        "mechanism_source": "V2/Final/generated/blender/cards-position-capture.json",
        "per_module": {
            "enclosure_halves": 2,
            "drum_components": 4,
            "cards": 64,
            "stickers": 128,
            "definitive_pawls": 1,
            "motor_components": 4,
            "m3_screws": 4,
            "m3_screw_objects": 16,
            "magnets": 6,
        },
        "display_pair": {
            "lower": "sticker_37_front",
            "upper": "sticker_38_back",
            "reason": "captured controller display position 37",
        },
        "stickers": {
            "background_rgb": list(BACKGROUND_RGB),
            "letter_rgb": list(LETTER_RGB),
            "finish": "gloss black",
            "font": str(FONT_PATH.relative_to(V2_DIR)),
            "all_128_faces_mapped": True,
            "base_atlas": "V2/Final/generated/blender/sticker-atlas.png",
            "typography": "production atlas with independent X/Y fit",
        },
        "fasteners": _fastener_layout(limits, enclosure, capture),
        "magnets": {
            "diameter_mm": enclosure["magnet_diameter"],
            "thickness_mm": enclosure["magnet_thickness"],
            "pocket_diameter_mm": enclosure["magnet_diameter"]
            + 2 * enclosure["magnet_radial_clearance"],
            "placements": _magnet_layout(limits, enclosure),
        },
        "motor_components": [
            {"name": name, "file": f"components/{name}.stl"}
            for name in MOTOR_COMPONENTS
        ],
        "modules": modules,
    }


def export_motor_components() -> None:
    COMPONENTS_DIR.mkdir(parents=True, exist_ok=True)
    components = {
        component.name: component.shape
        for component in captured_enclosure_design_components(CAPTURE_PATH)
    }
    for name in MOTOR_COMPONENTS:
        components[name].exportStl(
            str(COMPONENTS_DIR / f"{name}.stl"),
            tolerance=0.05,
            angularTolerance=0.1,
        )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_motor_components()
    write_licensed_json(OUTPUT_DIR / "manifest.json", build_manifest())


if __name__ == "__main__":
    main()
