#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Capture the manually adjusted Blender floor transform in millimetres."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
OUTPUT = BLENDER_DIR / "generated" / "floor-position.json"
OBJECT_NAME = "CompressionFloor_Adjustable"


def main() -> int:
    floor = bpy.data.objects[OBJECT_NAME]
    matrix = floor.matrix_world
    result = {
        "schema_version": 1,
        "object": OBJECT_NAME,
        "geometry_version": floor.get("geometry_version", 1),
        "origin_world_mm": [round(value * 1000, 6) for value in matrix.translation],
        "rotation_xyz_degrees": [
            round(math.degrees(value), 6) for value in matrix.to_euler("XYZ")
        ],
        "scale_xyz": [round(value, 9) for value in matrix.to_scale()],
        "origin_definition": "center of the 2 mm thick floor collider",
        "cad_status": "captured from Blender; defines simulation floor only",
    }
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
