#!/usr/bin/env python3
"""Validate the saved static HALLO/WELT! Blender scene."""

from __future__ import annotations

import json
from pathlib import Path

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BLENDER_DIR / "generated/hello-wall"


def main() -> None:
    collections = bpy.data.collections
    expected_counts = {
        "00_MODULE_ROOTS": 10,
        "01_ENCLOSURES_CAD": 30,
        "02_CARDS": 20,
        "03_STICKERS_GLOSS_BLACK_YELLOW": 20,
        "04_M3_SCREWS": 60,
    }
    actual_counts = {name: len(collections[name].objects) for name in expected_counts}
    roots = sorted(
        collections["00_MODULE_ROOTS"].objects,
        key=lambda obj: (obj["row"], obj["column"]),
    )
    displayed = "".join(obj["character"] for obj in roots)
    forbidden_tokens = ("motor", "electronic", "pcb", "backpack", "cable")
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
    checks = {
        "collection_counts": actual_counts == expected_counts,
        "displayed_characters": displayed == "HALLOWELT!",
        "spoken_message": bpy.context.scene["spoken_message"] == "HALLO WELT!",
        "electronics_absent": not forbidden_objects
        and bpy.context.scene["electronics_included"] is False,
        "textures_packed": not unpacked_images,
        "camera_present": bpy.context.scene.camera is not None,
    }
    result = {
        "valid": all(checks.values()),
        "checks": checks,
        "collection_counts": actual_counts,
        "displayed_characters": displayed,
        "spoken_message": bpy.context.scene["spoken_message"],
        "forbidden_objects": forbidden_objects,
        "unpacked_images": unpacked_images,
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
