#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Apply one settled card orientation set to another physical card profile."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

BLENDER_DIR = Path(__file__).resolve().parent
V2_DIR = BLENDER_DIR.parents[1]
CODE_DIR = V2_DIR / "Code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from json_license_metadata import validate_json_license, write_licensed_json


def _round(value: float) -> float:
    return round(value, 9)


def _card_outline(card: dict[str, float]) -> list[tuple[float, float]]:
    half_width = card["body_width"] / 2
    hinge = card["tab_axis_height"]
    tab_start = card["tab_start_height"]
    total = card["total_height"]
    tab_width = card["tab_width"]
    return [
        (-half_width, -hinge),
        (half_width, -hinge),
        (half_width, tab_start - hinge),
        (half_width + tab_width, tab_start - hinge),
        (half_width + tab_width, total - hinge),
        (-half_width - tab_width, total - hinge),
        (-half_width - tab_width, tab_start - hinge),
        (-half_width, tab_start - hinge),
    ]


def _polygon_centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    twice_area = 0.0
    x_sum = 0.0
    z_sum = 0.0
    for index, (x0, z0) in enumerate(points):
        x1, z1 = points[(index + 1) % len(points)]
        cross = x0 * z1 - x1 * z0
        twice_area += cross
        x_sum += (x0 + x1) * cross
        z_sum += (z0 + z1) * cross
    return x_sum / (3 * twice_area), z_sum / (3 * twice_area)


def _local_hinge(card: dict[str, float]) -> tuple[float, float, float]:
    center_x, center_z = _polygon_centroid(_card_outline(card))
    return (-center_x, 0.0, -center_z)


def _local_vertices(card: dict[str, float]) -> list[tuple[float, float, float]]:
    outline = _card_outline(card)
    center_x, center_z = _polygon_centroid(outline)
    half_thickness = card["thickness"] / 2
    return [
        (x - center_x, y, z - center_z)
        for y in (-half_thickness, half_thickness)
        for x, z in outline
    ]


def _matvec(
    matrix: list[list[float]], vector: tuple[float, float, float]
) -> tuple[float, float, float]:
    return tuple(
        sum(matrix[row][column] * vector[column] for column in range(3))
        for row in range(3)
    )


def _add(
    first: tuple[float, float, float], second: tuple[float, float, float]
) -> tuple[float, float, float]:
    return tuple(first[index] + second[index] for index in range(3))


def _subtract(
    first: tuple[float, float, float], second: tuple[float, float, float]
) -> tuple[float, float, float]:
    return tuple(first[index] - second[index] for index in range(3))


def _retarget_card(
    source_capture: dict[str, Any],
    source_card: dict[str, float],
    target_card: dict[str, float],
) -> dict[str, Any]:
    rotation = [row[:3] for row in source_capture["matrix_world"][:3]]
    source_origin = tuple(float(value) for value in source_capture["origin_world_mm"])
    world_hinge = _add(source_origin, _matvec(rotation, _local_hinge(source_card)))
    target_origin = _subtract(world_hinge, _matvec(rotation, _local_hinge(target_card)))

    world_vertices = [
        _add(target_origin, _matvec(rotation, vertex))
        for vertex in _local_vertices(target_card)
    ]
    result = copy.deepcopy(source_capture)
    result["origin_world_mm"] = [_round(value) for value in target_origin]
    result["matrix_world"] = copy.deepcopy(source_capture["matrix_world"])
    for axis in range(3):
        result["matrix_world"][axis][3] = _round(target_origin[axis] / 1000)
    result["bounds_world_mm"] = {
        "minimum": [
            _round(min(vertex[axis] for vertex in world_vertices)) for axis in range(3)
        ],
        "maximum": [
            _round(max(vertex[axis] for vertex in world_vertices)) for axis in range(3)
        ],
    }
    return result


def _combined_bounds(captures: list[dict[str, Any]]) -> dict[str, list[float]]:
    return {
        "minimum": [
            _round(
                min(capture["bounds_world_mm"]["minimum"][axis] for capture in captures)
            )
            for axis in range(3)
        ],
        "maximum": [
            _round(
                max(capture["bounds_world_mm"]["maximum"][axis] for capture in captures)
            )
            for axis in range(3)
        ],
    }


def retarget_capture(
    source_capture: dict[str, Any],
    source_scene: dict[str, Any],
    target_capture: dict[str, Any],
    target_scene: dict[str, Any],
) -> dict[str, Any]:
    """Keep source rotations and hinge positions while changing card geometry."""

    source_cards = {int(card["card_number"]): card for card in source_capture["cards"]}
    if set(source_cards) != set(range(64)):
        raise ValueError("source capture must contain cards 00 through 63")
    if source_capture["controller"] != target_capture["controller"]:
        raise ValueError("source and target captures must use the same drum position")

    cards = [
        _retarget_card(source_cards[number], source_scene["card"], target_scene["card"])
        for number in range(64)
    ]
    southern_cards = [
        card for card in cards if card["card_number"] == 0 or card["card_number"] >= 33
    ]
    result = copy.deepcopy(target_capture)
    result["physical_variant"] = target_scene["physical_variant"]
    result["cards"] = cards
    result["all_cards_bounds_world_mm"] = _combined_bounds(cards)
    result["southern_cards_bounds_world_mm"] = _combined_bounds(southern_cards)
    result["orientation_source"] = {
        "physical_variant": source_capture["physical_variant"],
        "rule": "same rotations and hinge axes; target card geometry retained",
    }
    result["status"] = (
        "Card orientations retargeted from the accepted Final capture; "
        "Prototype card bounds recomputed around the same hinge axes"
    )
    return result


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_json_license(data, str(path))
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-capture", type=Path, required=True)
    parser.add_argument("--source-scene", type=Path, required=True)
    parser.add_argument("--target-capture", type=Path, required=True)
    parser.add_argument("--target-scene", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = retarget_capture(
        _load(args.source_capture),
        _load(args.source_scene),
        _load(args.target_capture),
        _load(args.target_scene),
    )
    write_licensed_json(args.target_capture, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
