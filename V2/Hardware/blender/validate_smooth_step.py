#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Validate the long-running scene and one deliberately slow drum step."""

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
    initial_settle_frame = 360
    for frame in range(scene.frame_start, initial_settle_frame + 1):
        scene.frame_set(frame)

    rotating_names = (
        "motor_side",
        "shaft_side",
        "support_front",
        "support_back",
        "motor_shaft",
    )
    transforms_before = {
        name: bpy.data.objects[name].matrix_world.copy() for name in rotating_names
    }
    _, motor_end, settle_end = insert_smooth_step(controller, initial_settle_frame)
    for frame in range(initial_settle_frame + 1, settle_end + 1):
        scene.frame_set(frame)

    card_00 = bpy.data.objects["card_00"]
    card_01 = bpy.data.objects["card_01"]
    overlap_count = len(world_bvh(card_00).overlap(world_bvh(card_01)))
    floor = bpy.data.objects["CompressionFloor_Adjustable"]
    floor_vertices = [floor.matrix_world @ vertex.co for vertex in floor.data.vertices]
    floor_top_mm = max(vertex.z for vertex in floor_vertices) * 1000
    floor_front_y_mm = max(vertex.y for vertex in floor_vertices) * 1000
    pawl_y_mm = bpy.data.objects["CardStopPawl_Adjustable"].location.y * 1000
    anchor = bpy.data.objects["DrumHingeAnchor"]
    all_cards_are_active_rigid_bodies = all(
        card.rigid_body is not None and card.rigid_body.type == "ACTIVE"
        for card in (bpy.data.objects[f"card_{number:02d}"] for number in range(64))
    )
    rotating_components_moved = all(
        bpy.data.objects[name].matrix_world != transforms_before[name]
        and bpy.data.objects[name].parent == controller
        for name in rotating_names
    )
    physical_rotation_degrees = math.degrees(controller.rotation_euler.x)
    controller["step_count"] = 64
    unbounded_target, _, _ = insert_smooth_step(controller, settle_end)
    result = {
        "motor_end_frame": motor_end,
        "settle_end_frame": settle_end,
        "controller_rotation_degrees": round(physical_rotation_degrees, 6),
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
        "floor_top_z_mm": round(floor_top_mm, 6),
        "floor_front_edge_y_mm": round(floor_front_y_mm, 6),
        "pawl_y_mm": round(pawl_y_mm, 6),
        "scene_end_frame": scene.frame_end,
        "playback_loop_mode": scene.playback_loop_mode,
        "all_cards_are_active_rigid_bodies": all_cards_are_active_rigid_bodies,
        "drum_anchor_is_kinematic_active": (
            anchor.rigid_body.type == "ACTIVE" and anchor.rigid_body.kinematic
        ),
        "rotating_components_moved_together": rotating_components_moved,
        "step_after_first_revolution": unbounded_target,
        "substeps_per_frame": scene.rigidbody_world.substeps_per_frame,
        "solver_iterations": scene.rigidbody_world.solver_iterations,
    }
    print(json.dumps(result, indent=2))
    valid = (
        overlap_count == 0
        and result["card_01_is_in_front_of_card_00"]
        and abs(floor_top_mm + 75) < 0.001
        and abs(floor_front_y_mm - pawl_y_mm) < 0.001
        and scene.frame_end == 1_000_000
        and scene.playback_loop_mode == "STOP_END_FRAME"
        and all_cards_are_active_rigid_bodies
        and result["drum_anchor_is_kinematic_active"]
        and rotating_components_moved
        and unbounded_target == 65
    )
    if not valid:
        raise RuntimeError("long-running drum validation failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
