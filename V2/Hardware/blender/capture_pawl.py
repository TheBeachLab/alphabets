#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Capture the manually adjusted Blender pawl transform in millimetres."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
OUTPUT = BLENDER_DIR / "generated" / "pawl-position.json"
OBJECT_NAME = "CardStopPawl_Adjustable"


def main() -> int:
    pawl = bpy.data.objects[OBJECT_NAME]
    matrix = pawl.matrix_world
    location = matrix.translation
    rotation = matrix.to_euler("XYZ")
    result = {
        "schema_version": 2,
        "object": OBJECT_NAME,
        "geometry_version": pawl["geometry_version"],
        "support_edge_world_mm": [round(value * 1000, 6) for value in location],
        "rotation_xyz_degrees": [round(math.degrees(value), 6) for value in rotation],
        "scale_xyz": [round(value, 9) for value in matrix.to_scale()],
        "origin_definition": "center of the lower inner support edge",
        "cad_status": "captured from Blender; not yet transferred to CadQuery",
    }
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
