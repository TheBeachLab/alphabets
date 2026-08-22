#!/usr/bin/env python3
"""Validate the complete-mechanism HALLO/WELT! Blender scene."""

from __future__ import annotations

import json
from pathlib import Path

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BLENDER_DIR / "generated/hello-wall"
CAPTURE_PATH = BLENDER_DIR / "generated/cards-position-capture.json"


def main() -> None:
    capture = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))
    collections = bpy.data.collections
    expected_counts = {
        "00_MODULE_ROOTS": 10,
        "01_ENCLOSURE_CAD": 20,
        "02_DRUM_CAD": 40,
        "03_CARDS_CAPTURED": 640,
        "04_STICKERS": 1280,
        "05_PAWL_DEFINITIVE": 10,
        "06_M3_SCREWS": 60,
    }
    actual_counts = {name: len(collections[name].objects) for name in expected_counts}
    roots = sorted(
        collections["00_MODULE_ROOTS"].objects,
        key=lambda obj: (obj["row"], obj["column"]),
    )
    displayed = "".join(obj["character"] for obj in roots)
    forbidden_exact = {
        "motor_body",
        "motor_collar",
        "motor_backpack",
        "motor_shaft",
        "electronics_card_envelope",
    }
    forbidden_objects = sorted(
        obj.name for obj in bpy.context.scene.objects if obj.name in forbidden_exact
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
    checks = {
        "collection_counts": actual_counts == expected_counts,
        "displayed_characters": displayed == "HALLOWELT!",
        "spoken_message": bpy.context.scene["spoken_message"] == "HALLO WELT!",
        "electronics_absent": not forbidden_objects
        and bpy.context.scene["electronics_included"] is False,
        "textures_packed": not unpacked_images,
        "no_render_generated": bpy.context.scene["render_generated"] is False
        and bpy.context.scene.camera is None,
        "complete_mechanisms": all(root["complete_mechanism"] for root in roots),
        "captured_display_pair": (
            bpy.context.scene["display_lower_sticker"] == "sticker_37_front"
            and bpy.context.scene["display_upper_sticker"] == "sticker_38_back"
        ),
        # Blender stores object matrices as float32 in the .blend.
        "captured_card_transforms": card_transform_error < 5e-7,
        "two_display_halves_per_module": len(display_stickers) == 20,
        "remaining_stickers_use_yellow_atlas": len(atlas_stickers) == 1260,
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
        "blend": bpy.data.filepath,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not result["valid"]:
        raise RuntimeError(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
