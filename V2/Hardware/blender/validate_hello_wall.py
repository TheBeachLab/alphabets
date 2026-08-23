#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Validate the complete-mechanism HALLO/WELT! Blender scene."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
V2_DIR = BLENDER_DIR.parents[1]
CODE_DIR = V2_DIR / "Code"
OUTPUT_DIR = V2_DIR / "Final/generated/blender/hello-wall"
CAPTURE_PATH = V2_DIR / "Final/generated/blender/cards-position-capture.json"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from json_license_metadata import validate_json_license, write_licensed_json


def main() -> None:
    capture = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))
    validate_json_license(capture, str(CAPTURE_PATH))
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_json_license(manifest, str(manifest_path))
    collections = bpy.data.collections
    expected_counts = {
        "00_MODULE_ROOTS": 10,
        "01_ENCLOSURE_CAD": 20,
        "02_DRUM_CAD": 40,
        "03_CARDS_CAPTURED": 640,
        "04_STICKERS": 1280,
        "05_PAWL_DEFINITIVE": 10,
        "06_M3_SCREWS": 160,
        "07_MOTORS_NO_CABLES": 40,
        "08_MAGNETS": 60,
        "09_CAMERA_AND_HDRI": 1,
    }
    actual_counts = {name: len(collections[name].objects) for name in expected_counts}
    roots = sorted(
        collections["00_MODULE_ROOTS"].objects,
        key=lambda obj: (obj["row"], obj["column"]),
    )
    displayed = "".join(obj["character"] for obj in roots)
    forbidden_tokens = ("electronics_card", "pcb", "cable")
    forbidden_objects = sorted(
        obj.name
        for obj in bpy.context.scene.objects
        if any(token in obj.name.lower() for token in forbidden_tokens)
    )
    unpacked_images = sorted(
        image.name
        for image in bpy.data.images
        if image.source == "FILE" and image.packed_file is None
    )
    captured_matrices = {
        int(item["card_number"]): item["matrix_world"] for item in capture["cards"]
    }
    card_transform_error = max(
        abs(
            obj.matrix_local[row][column]
            - captured_matrices[int(obj["card_number"])][row][column]
        )
        for obj in collections["03_CARDS_CAPTURED"].objects
        for row in range(4)
        for column in range(4)
    )
    display_stickers = [
        obj for obj in collections["04_STICKERS"].objects if "display_character" in obj
    ]
    atlas_stickers = [
        obj
        for obj in collections["04_STICKERS"].objects
        if obj.active_material
        and obj.active_material.name == "StickerAtlas_GlossBlack_Yellow"
    ]
    hdri_images = [
        node.image
        for node in bpy.context.scene.world.node_tree.nodes
        if node.type == "TEX_ENVIRONMENT" and node.image is not None
    ]
    expected_magnets = {
        placement["name"]: placement["center_mm"]
        for placement in manifest["magnets"]["placements"]
    }
    magnet_position_error = max(
        abs(
            obj.matrix_local.translation[index] * 1000
            - expected_magnets[obj.name.split("_R")[0].removeprefix("Magnet_")][index]
        )
        for obj in collections["08_MAGNETS"].objects
        for index in range(3)
    )
    checks = {
        "collection_counts": actual_counts == expected_counts,
        "displayed_characters": displayed == "HALLOWELT!",
        "spoken_message": bpy.context.scene["spoken_message"] == "HALLO WELT!",
        "electronics_absent": not forbidden_objects
        and bpy.context.scene["electronics_included"] is False,
        "motors_present_without_cables": bpy.context.scene["motor_included"] is True
        and all(
            obj["cables_included"] is False
            for obj in collections["07_MOTORS_NO_CABLES"].objects
        ),
        "textures_packed": not unpacked_images,
        "no_render_generated": bpy.context.scene["render_generated"] is False,
        "camera_present": bpy.context.scene.camera is not None,
        "packed_hdri_present": len(hdri_images) == 1
        and hdri_images[0].packed_file is not None,
        "complete_mechanisms": all(root["complete_mechanism"] for root in roots),
        "captured_display_pair": (
            bpy.context.scene["display_lower_sticker"] == "sticker_37_front"
            and bpy.context.scene["display_upper_sticker"] == "sticker_38_back"
        ),
        # Blender stores object matrices as float32 in the .blend.
        "captured_card_transforms": card_transform_error < 5e-7,
        "two_display_halves_per_module": len(display_stickers) == 20,
        "all_stickers_use_production_yellow_atlas": len(atlas_stickers) == 1280,
        "uppercase_w_and_o": all(
            obj["display_character"] in "HALOWET!" for obj in display_stickers
        )
        and not any(obj["display_character"] in "wo" for obj in display_stickers),
        "screws_use_cad_positions": all(
            obj["cad_derived_position"] is True
            for obj in collections["06_M3_SCREWS"].objects
        ),
        "magnets_use_cad_pockets": magnet_position_error < 1e-5,
    }
    result = {
        "valid": all(checks.values()),
        "checks": checks,
        "collection_counts": actual_counts,
        "displayed_characters": displayed,
        "spoken_message": bpy.context.scene["spoken_message"],
        "forbidden_objects": forbidden_objects,
        "unpacked_images": unpacked_images,
        "maximum_card_transform_error": card_transform_error,
        "display_sticker_count": len(display_stickers),
        "yellow_atlas_sticker_count": len(atlas_stickers),
        "maximum_magnet_position_error_mm": magnet_position_error,
        "hdri_images": [image.name for image in hdri_images],
        "blend": bpy.data.filepath,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_licensed_json(OUTPUT_DIR / "validation.json", result)
    if not result["valid"]:
        raise RuntimeError(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
