#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Validate appended drum steps beyond the initial rigid-body cache range."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
if str(BLENDER_DIR) not in sys.path:
    sys.path.insert(0, str(BLENDER_DIR))
sys.modules.pop("alphabets_drum_step", None)

from alphabets_drum_step import extend_simulation_range, insert_smooth_steps


def parse_args() -> argparse.Namespace:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--stale-scene-end", type=int)
    return parser.parse_args(arguments)


def evaluate_until(scene: bpy.types.Scene, end_frame: int) -> None:
    for frame in range(scene.frame_current + 1, end_frame + 1):
        scene.frame_set(frame)


def main() -> int:
    args = parse_args()
    scene = bpy.context.scene
    controller = bpy.data.objects["DrumStepController"]
    scene.frame_set(800)
    if args.stale_scene_end is not None:
        scene.frame_end = args.stale_scene_end
        scene.rigidbody_world.point_cache.frame_end = 800

    if args.single:
        for _ in range(args.steps):
            _, _, settle_end = insert_smooth_steps(controller, scene.frame_current, 1)
            extend_simulation_range(scene, settle_end)
            evaluate_until(scene, settle_end)
    else:
        _, _, settle_end = insert_smooth_steps(
            controller, scene.frame_current, args.steps
        )
        extend_simulation_range(scene, settle_end)
        evaluate_until(scene, settle_end)

    cards = [obj for obj in bpy.data.objects if obj.name.startswith("card_")]
    matrix_values = [
        value for card in cards for row in card.matrix_world for value in row
    ]
    max_distance = max(card.matrix_world.translation.length for card in cards)
    movement_end = 800 + args.steps * (
        int(controller["step_duration_frames"]) + int(controller["settle_frames"])
    )
    expected_range_end = max(movement_end, args.stale_scene_end or movement_end)
    valid = all(
        (
            int(controller["step_count"]) == args.steps,
            scene.frame_current == movement_end,
            scene.frame_end == expected_range_end,
            scene.rigidbody_world.point_cache.frame_end == expected_range_end,
            all(math.isfinite(value) for value in matrix_values),
            max_distance < 1,
        )
    )
    result = {
        "mode": "single" if args.single else "batch",
        "steps": args.steps,
        "frame": scene.frame_current,
        "scene_end": scene.frame_end,
        "rigid_body_cache_end": scene.rigidbody_world.point_cache.frame_end,
        "max_card_distance_m": round(max_distance, 6),
        "valid": valid,
    }
    print(json.dumps(result, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
