#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Generate deterministic CadQuery meshes, texture atlas, and Blender metadata."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BLENDER_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = BLENDER_DIR.parents[3]
MECHANICAL_DIR = BLENDER_DIR.parent / "mechanical"
STICKERS_DIR = BLENDER_DIR.parent / "stickers"
LICENSES_DIR = REPOSITORY_ROOT / "LICENSES"
GENERATED_DIR = BLENDER_DIR / "generated"

for source_dir in (LICENSES_DIR, MECHANICAL_DIR, STICKERS_DIR):
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

import cadquery as cq
from alphabets_cad.assemblies import (
    BACKPACK,
    MOTOR,
    SHAFT,
    _orient_for_enclosure,
    _rotate_drum_to_stop,
    drum_components,
    drum_stop_rotation_degrees,
)
from alphabets_cad.parameters import DESIGN
from alphabets_cad.parts import motor_components
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

ATLAS_COLUMNS = 16
ATLAS_ROWS = 4
ATLAS_WIDTH_PX = 4096
ATLAS_HEIGHT_PX = 2071
NORTH_FALL_BIAS_DEGREES = 0.5


def _round(value: float) -> float:
    return round(value, 9)


def build_sticker_mapping() -> dict[str, Any]:
    """Map all 128 physical sticker faces onto one 64-character atlas."""

    profile = load_profile("international-64", None)
    if len(profile.characters) != DESIGN.drum.positions:
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
                DESIGN.card.sticker_width,
                2 * DESIGN.card.sticker_face_height,
            ],
            "split_y_mm": DESIGN.card.sticker_face_height,
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
    card = DESIGN.card
    drum = DESIGN.drum
    step_degrees = 360 / drum.positions
    stop_degrees = drum_stop_rotation_degrees(DESIGN)
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
            "initial_top_z_mm": -95,
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
    profile = load_profile("international-64", None)
    face = FontFace.load(DEFAULT_FONT, DEFAULT_FONT_WEIGHT, DEFAULT_FONT_WIDTH)
    geometry = SheetGeometry(
        card_width_mm=DESIGN.card.sticker_width,
        card_height_mm=2 * DESIGN.card.sticker_face_height,
        margin_mm=0,
        column_gap_mm=0,
        row_gap_mm=0,
        columns=ATLAS_COLUMNS,
        glyph_padding_x_mm=3,
        glyph_padding_y_mm=4,
        split_y_mm=DESIGN.card.sticker_face_height,
        bleed_mm=0,
        use_condensed_overrides=True,
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
    drum_offset = -DESIGN.drum_outer_width / 2
    static_shapes = [
        (
            component.name,
            _orient_for_enclosure(
                _rotate_drum_to_stop(component.shape, DESIGN), drum_offset
            ),
            component.color,
        )
        for component in drum_components(DESIGN)
    ]
    motor_offset = -DESIGN.enclosure_outer_width / 2
    motor_colors = {
        "motor_body": MOTOR,
        "motor_collar": MOTOR,
        "motor_backpack": BACKPACK,
        "motor_shaft": SHAFT,
    }
    static_shapes.extend(
        (
            name,
            _orient_for_enclosure(
                shape.rotate((0, 0, 0), (0, 0, 1), 90)
                if name == "motor_shaft"
                else shape,
                motor_offset,
            ),
            motor_colors[name],
        )
        for name, shape in motor_components(DESIGN).items()
    )
    for name, shape, color in static_shapes:
        path = mesh_dir / f"{name}.stl"
        cq.exporters.export(
            shape,
            str(path),
            tolerance=0.05,
            angularTolerance=0.1,
        )
        embed_artifact_license(path)
        components.append(
            {
                "name": name,
                "file": str(path.relative_to(GENERATED_DIR)),
                "color": list(color.toTuple()),
            }
        )
    return components


def main() -> int:
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
