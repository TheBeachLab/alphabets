#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Generate deterministic CadQuery meshes, texture atlas, and Blender metadata."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BLENDER_DIR = Path(__file__).resolve().parent
V2_DIR = BLENDER_DIR.parents[1]
MECHANICAL_DIR = V2_DIR / "Hardware" / "mechanical"
STICKERS_DIR = V2_DIR / "Hardware" / "stickers"
CODE_DIR = V2_DIR / "Code"
GENERATED_DIR = V2_DIR / "Final/generated/blender"

for source_dir in (CODE_DIR, MECHANICAL_DIR, STICKERS_DIR):
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

import cadquery as cq
from alphabets_cad.assemblies import (
    drum_stop_rotation_degrees,
    enclosed_module_components,
)
from alphabets_cad.parameters import DESIGN, DesignParameters, load_design_profile
from artifact_license_metadata import embed_artifact_license
from generate_stickers import (
    DEFAULT_FONT,
    DEFAULT_FONT_WEIGHT,
    DEFAULT_FONT_WIDTH,
    FontFace,
    SheetGeometry,
    build_svg,
    load_profile,
)
from json_license_metadata import JSON_LICENSE_METADATA
from physical_variants import load_variant

ATLAS_COLUMNS = 16
ATLAS_ROWS = 4
ATLAS_WIDTH_PX = 4096
ATLAS_HEIGHT_PX = 2071
EXCLUDED_STATIC_COMPONENTS = frozenset({"enclosure_lower", "enclosure_upper"})
NORTH_FALL_BIAS_DEGREES = 0.5
ACTIVE_DESIGN: DesignParameters = DESIGN
ACTIVE_CHARACTER_PRESET = "international-64"
ACTIVE_VARIANT = "definitive"


def _round(value: float) -> float:
    return round(value, 9)


def build_sticker_mapping() -> dict[str, Any]:
    """Map all 128 physical sticker faces onto one 64-character atlas."""

    profile = load_profile(ACTIVE_CHARACTER_PRESET, None)
    if len(profile.characters) != ACTIVE_DESIGN.drum.positions:
        raise ValueError("the Blender atlas requires exactly 64 characters")

    assignments: list[dict[str, Any]] = []
    for character_index, character in enumerate(profile.characters):
        row, column = divmod(character_index, ATLAS_COLUMNS)
        u0 = column / ATLAS_COLUMNS
        u1 = (column + 1) / ATLAS_COLUMNS
        cell_v0 = 1 - (row + 1) / ATLAS_ROWS
        cell_v1 = 1 - row / ATLAS_ROWS
        split_v = (cell_v0 + cell_v1) / 2

        assignments.extend(
            (
                {
                    "target": f"sticker_{character_index:02d}_front",
                    "card": character_index,
                    "face": "front",
                    "display_half": "lower",
                    "character_index": character_index,
                    "character": character,
                    "atlas_cell": {"row": row, "column": column},
                    "uv_box": [
                        _round(u0),
                        _round(cell_v0),
                        _round(u1),
                        _round(split_v),
                    ],
                    "rotation_degrees": 0,
                    "horizontal_flip": True,
                    "center_cut_edge": "top",
                    "target_edge": "hinge",
                },
                {
                    "target": f"sticker_{(character_index + 1) % 64:02d}_back",
                    "card": (character_index + 1) % 64,
                    "face": "back",
                    "display_half": "upper",
                    "character_index": character_index,
                    "character": character,
                    "atlas_cell": {"row": row, "column": column},
                    "uv_box": [
                        _round(u0),
                        _round(split_v),
                        _round(u1),
                        _round(cell_v1),
                    ],
                    # The upper artwork is applied upside down on the reverse
                    # face. It becomes upright after the flap turns over.
                    "rotation_degrees": 180,
                    "horizontal_flip": False,
                    "center_cut_edge": "bottom",
                    "target_edge": "hinge",
                },
            )
        )

    return {
        **JSON_LICENSE_METADATA,
        "schema_version": 1,
        "physical_variant": ACTIVE_VARIANT,
        "character_set": {
            "id": profile.id,
            "characters": profile.characters,
        },
        "atlas": {
            "file": "sticker-atlas.png",
            "source_svg": "sticker-atlas.svg",
            "columns": ATLAS_COLUMNS,
            "rows": ATLAS_ROWS,
            "width_px": ATLAS_WIDTH_PX,
            "height_px": ATLAS_HEIGHT_PX,
            "cell_mm": [
                ACTIVE_DESIGN.card.sticker_width,
                2 * ACTIVE_DESIGN.card.sticker_face_height,
            ],
            "split_y_mm": ACTIVE_DESIGN.card.sticker_face_height,
        },
        "numbering": {
            "card_00": "lower front stop position",
            "card_01": "upper front stop position",
            "direction": "increasing in anticlockwise travel from motor-side view",
            "lower_half_target": "sticker_i_front",
            "upper_half_target": "sticker_(i+1 mod 64)_back",
        },
        "assignments": sorted(assignments, key=lambda item: item["target"]),
    }


def build_scene_manifest(static_components: list[dict[str, Any]]) -> dict[str, Any]:
    card = ACTIVE_DESIGN.card
    drum = ACTIVE_DESIGN.drum
    step_degrees = 360 / drum.positions
    stop_degrees = drum_stop_rotation_degrees(ACTIVE_DESIGN)
    front_lower_position = drum.positions // 2
    poses: list[dict[str, Any]] = []
    for position in range(drum.positions):
        angle_degrees = 180 - stop_degrees - position * step_degrees
        angle_radians = math.radians(angle_degrees)
        card_number = (front_lower_position - position) % drum.positions
        pivot_z = drum.flap_hole_center_radius * math.sin(angle_radians)
        poses.append(
            {
                "card": card_number,
                "source_hole_position": position,
                "pivot_mm": [
                    0,
                    _round(drum.flap_hole_center_radius * math.cos(angle_radians)),
                    _round(pivot_z),
                ],
                "tilt_degrees": 0 if pivot_z < 0 else 180 - NORTH_FALL_BIAS_DEGREES,
                "radial_tilt_degrees": _round(angle_degrees + 90),
            }
        )

    # Release from the rear through the southern hemisphere to the lower
    # front card, then from the rear over the northern hemisphere toward the
    # upper front card. This reproduces the physical shingling order and avoids
    # the perfectly symmetric radial ring locking itself before gravity acts.
    release_order = [*range(33, 64), 0, *range(32, 0, -1)]
    poses_by_card = {pose["card"]: pose for pose in poses}

    card_01_hole = poses_by_card[1]["pivot_mm"]
    card_02_hole = poses_by_card[2]["pivot_mm"]
    support_height = _round((card_01_hole[2] + card_02_hole[2]) / 2)
    card_01_finished_front_y = _round(card_01_hole[1] + card.finished_thickness / 2)

    return {
        **JSON_LICENSE_METADATA,
        "schema_version": 1,
        "physical_variant": ACTIVE_VARIANT,
        "units": "millimetres",
        "card": {
            "body_width": card.body_width,
            "total_height": card.total_height,
            "tab_width": card.tab_width,
            "tab_height": card.tab_height,
            "tab_start_height": card.tab_start_height,
            "tab_axis_height": card.tab_axis_height,
            "thickness": card.thickness,
            "finished_thickness": card.finished_thickness,
            "sticker_width": card.sticker_width,
            "sticker_face_height": card.sticker_face_height,
            "sticker_y_offset": card.sticker_y_offset,
        },
        "drum": {
            "positions": drum.positions,
            "flap_hole_center_radius": drum.flap_hole_center_radius,
            "stop_rotation_degrees": stop_degrees,
        },
        "drum_step": {
            "controller": "DrumStepController",
            "property": "step_count",
            "degrees_per_step": _round(-360 / drum.positions),
            "direction": "anticlockwise from motor side at negative X",
            "rotating_components": [
                "motor_side",
                "shaft_side",
                "support_front",
                "support_back",
                "motor_shaft",
            ],
        },
        "manual_floor": {
            "geometry_version": 1,
            "size_mm": 250,
            "thickness_mm": 2,
            "initial_top_z_mm": -75,
            "long_run_top_z_mm": -75,
            "long_run_end_frame": 1_000_000,
            "long_run_ready_frame": 360,
        },
        "pawl": {
            "name": "CardStopPawl_Adjustable",
            "geometry_version": 2,
            "support_edge_initial_mm": [
                0,
                card_01_finished_front_y,
                support_height,
            ],
            "width_mm": 6,
            "height_mm": 8,
            "thickness_mm": 1,
            "reference_card_01_hole_mm": card_01_hole,
            "reference_card_02_hole_mm": card_02_hole,
            "flush_reference": "finished front face of vertical card_01",
            "mount": "fixed to enclosure; never rotates with drum",
        },
        "simulation": {
            "gravity_m_s2": 9.81,
            "release_start_frame": 5,
            "release_interval_frames": 3,
            "north_fall_bias_degrees": NORTH_FALL_BIAS_DEGREES,
            "card_center_of_mass_bias_y_mm": 0.05,
            "release_order": release_order,
            "end_frame": 800,
        },
        "card_poses": sorted(poses, key=lambda item: item["card"]),
        "static_components": static_components,
    }


def write_atlas() -> None:
    profile = load_profile(ACTIVE_CHARACTER_PRESET, None)
    face = FontFace.load(DEFAULT_FONT, DEFAULT_FONT_WEIGHT, DEFAULT_FONT_WIDTH)
    geometry = SheetGeometry(
        card_width_mm=ACTIVE_DESIGN.card.sticker_width,
        card_height_mm=2 * ACTIVE_DESIGN.card.sticker_face_height,
        margin_mm=0,
        column_gap_mm=0,
        row_gap_mm=0,
        columns=ATLAS_COLUMNS,
        glyph_padding_x_mm=3,
        glyph_padding_y_mm=4,
        split_y_mm=ACTIVE_DESIGN.card.sticker_face_height,
    )
    svg, _ = build_svg(
        profile,
        [face],
        geometry,
        "#000000",
        "#FFFFFF",
        "#FF00FF",
        False,
        False,
    )
    svg_path = GENERATED_DIR / "sticker-atlas.svg"
    png_path = GENERATED_DIR / "sticker-atlas.png"
    svg_path.write_text(svg, encoding="utf-8")
    embed_artifact_license(svg_path)
    magick = shutil.which("magick")
    if magick is None:
        raise RuntimeError("ImageMagick 'magick' is required to rasterize the atlas")
    subprocess.run(
        [
            magick,
            "-background",
            "black",
            str(svg_path),
            "-resize",
            f"{ATLAS_WIDTH_PX}x{ATLAS_HEIGHT_PX}!",
            "-alpha",
            "off",
            str(png_path),
        ],
        check=True,
    )
    embed_artifact_license(png_path)


def export_static_meshes() -> list[dict[str, Any]]:
    mesh_dir = GENERATED_DIR / "meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    components: list[dict[str, Any]] = []
    for component in enclosed_module_components(ACTIVE_DESIGN, exploded=False):
        if component.name in EXCLUDED_STATIC_COMPONENTS:
            stale_path = mesh_dir / f"{component.name}.stl"
            stale_path.unlink(missing_ok=True)
            continue
        if component.name.startswith(("card_", "sticker_")):
            continue
        path = mesh_dir / f"{component.name}.stl"
        cq.exporters.export(
            component.shape,
            str(path),
            tolerance=0.05,
            angularTolerance=0.1,
        )
        embed_artifact_license(path)
        components.append(
            {
                "name": component.name,
                "file": str(path.relative_to(GENERATED_DIR)),
                "color": list(component.color.toTuple()),
            }
        )
    return components


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--variant", choices=("prototype", "definitive"), default="definitive"
    )
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--output", type=Path, default=GENERATED_DIR)
    return parser.parse_args()


def main() -> int:
    global ACTIVE_CHARACTER_PRESET, ACTIVE_DESIGN, ACTIVE_VARIANT, GENERATED_DIR
    args = parse_args()
    variant = load_variant(args.variant)
    profile_path = args.profile or (
        V2_DIR / ("Prototype" if variant.id == "prototype" else "Final") / "design.toml"
    )
    ACTIVE_DESIGN = load_design_profile(profile_path, base=DESIGN)
    ACTIVE_CHARACTER_PRESET = variant.character_preset
    ACTIVE_VARIANT = variant.id
    GENERATED_DIR = args.output.resolve()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    write_atlas()
    mapping = build_sticker_mapping()
    (GENERATED_DIR / "sticker-mapping.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    static_components = export_static_meshes()
    scene = build_scene_manifest(static_components)
    (GENERATED_DIR / "scene.json").write_text(
        json.dumps(scene, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
