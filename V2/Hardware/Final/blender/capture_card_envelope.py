#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Capture the settled card envelope from the currently loaded Blender file."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = BLENDER_DIR.parents[3]
LICENSES_DIR = REPOSITORY_ROOT / "LICENSES"
GENERATED_DIR = BLENDER_DIR / "generated"
MM_PER_M = 1000.0
if str(LICENSES_DIR) not in sys.path:
    sys.path.insert(0, str(LICENSES_DIR))

from json_license_metadata import JSON_LICENSE_METADATA


def repository_path(path: Path) -> str:
    """Return stable repository-relative provenance across linked worktrees."""

    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPOSITORY_ROOT))
    except ValueError:
        if "V2" in resolved.parts:
            return str(Path(*resolved.parts[resolved.parts.index("V2") :]))
        return str(resolved)


def parse_args() -> argparse.Namespace:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=GENERATED_DIR / "card-envelope.json",
    )
    return parser.parse_args(arguments)


def source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    source_path = Path(bpy.data.filepath).resolve()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    drum_side = bpy.data.objects["motor_side"].evaluated_get(depsgraph)
    drum_radius_mm = max(
        math.hypot(world.y, world.z) * MM_PER_M
        for vertex in drum_side.data.vertices
        for world in (drum_side.matrix_world @ vertex.co,)
    )

    extrema: dict[str, dict[str, Any]] = {}
    for obj in bpy.data.objects:
        if not (obj.name.startswith("card_") or obj.name.startswith("sticker_")):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        if evaluated.type != "MESH":
            continue
        for vertex in evaluated.data.vertices:
            world = evaluated.matrix_world @ vertex.co
            point_mm = tuple(coordinate * MM_PER_M for coordinate in world)
            for key, value in (("upper", point_mm[2]), ("lower", -point_mm[2])):
                current = extrema.get(key)
                if current is None or value > current["distance_from_axis_mm"]:
                    extrema[key] = {
                        "distance_from_axis_mm": value,
                        "object": obj.name,
                        "world_mm": [round(coordinate, 6) for coordinate in point_mm],
                    }

    if set(extrema) != {"upper", "lower"}:
        raise RuntimeError("card envelope could not be measured")

    upper_height_mm = extrema["upper"]["distance_from_axis_mm"]
    lower_height_mm = extrema["lower"]["distance_from_axis_mm"]
    result = {
        **JSON_LICENSE_METADATA,
        "schema_version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "source_blend": repository_path(source_path),
        "source_blend_sha256": source_sha256(source_path),
        "frame": bpy.context.scene.frame_current,
        "controller_step_count": int(
            bpy.data.objects["DrumStepController"].get("step_count", 0)
        ),
        "drum_radius_mm": drum_radius_mm,
        "upper": {
            **extrema["upper"],
            "protrusion_above_drum_mm": round(upper_height_mm - drum_radius_mm, 6),
        },
        "lower_measured_reference": {
            **extrema["lower"],
            "protrusion_below_drum_mm": round(lower_height_mm - drum_radius_mm, 6),
        },
        "enclosure_rule": (
            "use the upper distance from the drum axis for both symmetric halves"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
