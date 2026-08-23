#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Capture the live rigid-body card transforms from the currently open scene."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = BLENDER_DIR.parents[3]
LICENSES_DIR = REPOSITORY_ROOT / "LICENSES"
GENERATED_DIR = BLENDER_DIR / "generated"
JSON_PATH = GENERATED_DIR / "cards-position-capture.json"
BLEND_PATH = GENERATED_DIR / "alphabets-v2-card-positions.blend"
MM = 1000
if str(LICENSES_DIR) not in sys.path:
    sys.path.insert(0, str(LICENSES_DIR))

from json_license_metadata import write_licensed_json


def repository_path(path: Path) -> str:
    """Return stable repository-relative provenance across linked worktrees."""

    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPOSITORY_ROOT))
    except ValueError:
        if "V2" in resolved.parts:
            return str(Path(*resolved.parts[resolved.parts.index("V2") :]))
        return str(resolved)


def rounded(values: list[float] | tuple[float, ...]) -> list[float]:
    return [round(value, 9) for value in values]


def object_capture(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> dict:
    evaluated = obj.evaluated_get(depsgraph)
    matrix = evaluated.matrix_world.copy()
    bounds = [matrix @ vertex.co for vertex in evaluated.data.vertices]
    quaternion = matrix.to_quaternion()
    return {
        "name": obj.name,
        "matrix_world": [rounded(list(row)) for row in matrix],
        "origin_world_mm": rounded([value * MM for value in matrix.translation]),
        "rotation_quaternion_wxyz": rounded(list(quaternion)),
        "bounds_world_mm": {
            "minimum": rounded(
                [min(corner[axis] for corner in bounds) * MM for axis in range(3)]
            ),
            "maximum": rounded(
                [max(corner[axis] for corner in bounds) * MM for axis in range(3)]
            ),
        },
    }


def combined_bounds(captures: list[dict]) -> dict:
    return {
        "minimum": [
            round(
                min(
                    capture["bounds_world_mm"]["minimum"][axis] for capture in captures
                ),
                9,
            )
            for axis in range(3)
        ],
        "maximum": [
            round(
                max(
                    capture["bounds_world_mm"]["maximum"][axis] for capture in captures
                ),
                9,
            )
            for axis in range(3)
        ],
    }


def main() -> int:
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cards = []
    for number in range(64):
        capture = object_capture(bpy.data.objects[f"card_{number:02d}"], depsgraph)
        capture["card_number"] = number
        cards.append(capture)

    southern_cards = [
        capture
        for capture in cards
        if capture["card_number"] == 0 or capture["card_number"] >= 33
    ]
    controller = bpy.data.objects["DrumStepController"]
    completed_steps = int(controller.get("step_count", 0))
    data = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "source_blend": repository_path(Path(bpy.data.filepath)),
        "capture_frame": scene.frame_current,
        "controller": {
            "completed_steps": completed_steps,
            "display_position": completed_steps % 64,
            "completed_revolutions": completed_steps // 64,
            "rotation_x_degrees": round(
                controller.rotation_euler.x * 180 / 3.141592653589793, 9
            ),
        },
        "cards": cards,
        "all_cards_bounds_world_mm": combined_bounds(cards),
        "southern_cards_bounds_world_mm": combined_bounds(southern_cards),
        "floor": object_capture(
            bpy.data.objects["CompressionFloor_Adjustable"], depsgraph
        ),
        "pawl": object_capture(bpy.data.objects["CardStopPawl_Adjustable"], depsgraph),
        "status": "Blender simulation snapshot; not yet transferred to CadQuery",
    }
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    write_licensed_json(JSON_PATH, data)
    if Path(bpy.data.filepath).resolve() != BLEND_PATH.resolve():
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), copy=True)
    print(
        json.dumps(
            {
                "json": str(JSON_PATH),
                "blend": str(BLEND_PATH),
                "frame": scene.frame_current,
                "position": completed_steps % 64,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
