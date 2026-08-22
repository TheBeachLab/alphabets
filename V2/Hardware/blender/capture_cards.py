#!/usr/bin/env python3
"""Capture the live rigid-body card transforms from the currently open scene."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BLENDER_DIR / "generated"
JSON_PATH = GENERATED_DIR / "cards-position-capture.json"
BLEND_PATH = GENERATED_DIR / "alphabets-v2-card-positions.blend"
MM = 1000


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
        "source_blend": bpy.data.filepath,
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
    JSON_PATH.write_text(json.dumps(data, indent=2) + "\n")
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
