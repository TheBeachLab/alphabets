#!/usr/bin/env python3
"""Validate one smooth drum step against card-to-card tunnelling."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

BLENDER_DIR = Path(__file__).resolve().parent
if str(BLENDER_DIR) not in sys.path:
    sys.path.insert(0, str(BLENDER_DIR))

from alphabets_drum_step import insert_smooth_step


def world_bvh(obj: bpy.types.Object) -> BVHTree:
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    polygons = [tuple(polygon.vertices) for polygon in obj.data.polygons]
    return BVHTree.FromPolygons(vertices, polygons)


def main() -> int:
    scene = bpy.context.scene
    controller = bpy.data.objects["DrumStepController"]
    initial_settle_frame = 230
    for frame in range(scene.frame_start, initial_settle_frame + 1):
        scene.frame_set(frame)

    _, motor_end, settle_end = insert_smooth_step(controller, initial_settle_frame)
    for frame in range(initial_settle_frame + 1, settle_end + 1):
        scene.frame_set(frame)

    card_00 = bpy.data.objects["card_00"]
    card_01 = bpy.data.objects["card_01"]
    overlap_count = len(world_bvh(card_00).overlap(world_bvh(card_01)))
    result = {
        "motor_end_frame": motor_end,
        "settle_end_frame": settle_end,
        "controller_rotation_degrees": round(
            math.degrees(controller.rotation_euler.x), 6
        ),
        "card_00_center_mm": [
            round(value * 1000, 6) for value in card_00.matrix_world.translation
        ],
        "card_01_center_mm": [
            round(value * 1000, 6) for value in card_01.matrix_world.translation
        ],
        "card_00_card_01_surface_intersections": overlap_count,
        "card_01_is_in_front_of_card_00": (
            card_01.matrix_world.translation.y > card_00.matrix_world.translation.y
        ),
        "substeps_per_frame": scene.rigidbody_world.substeps_per_frame,
        "solver_iterations": scene.rigidbody_world.solver_iterations,
    }
    print(json.dumps(result, indent=2))
    return 0 if overlap_count == 0 and result["card_01_is_in_front_of_card_00"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
