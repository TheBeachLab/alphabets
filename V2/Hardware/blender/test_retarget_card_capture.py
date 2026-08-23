# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from pathlib import Path

import pytest
from retarget_card_capture import (
    _add,
    _local_hinge,
    _matvec,
    retarget_capture,
)

V2_DIR = Path(__file__).resolve().parents[2]
FINAL = V2_DIR / "Final/generated/blender"
PROTOTYPE = V2_DIR / "Prototype/generated/blender"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _hinge_world(capture: dict, card: dict[str, float]) -> tuple[float, ...]:
    rotation = [row[:3] for row in capture["matrix_world"][:3]]
    origin = tuple(capture["origin_world_mm"])
    return _add(origin, _matvec(rotation, _local_hinge(card)))


def test_prototype_reuses_final_rotations_around_the_same_hinge_axes() -> None:
    final_capture = _load(FINAL / "cards-position-capture.json")
    final_scene = _load(FINAL / "scene.json")
    prototype_capture = _load(PROTOTYPE / "cards-position-capture.json")
    prototype_scene = _load(PROTOTYPE / "scene.json")

    result = retarget_capture(
        final_capture,
        final_scene,
        prototype_capture,
        prototype_scene,
    )
    assert result["physical_variant"] == "prototype"
    assert result["orientation_source"]["physical_variant"] == "definitive"

    for final_card, prototype_card in zip(
        final_capture["cards"], result["cards"], strict=True
    ):
        assert prototype_card["card_number"] == final_card["card_number"]
        assert (
            prototype_card["rotation_quaternion_wxyz"]
            == final_card["rotation_quaternion_wxyz"]
        )
        assert [row[:3] for row in prototype_card["matrix_world"][:3]] == [
            row[:3] for row in final_card["matrix_world"][:3]
        ]
        assert _hinge_world(prototype_card, prototype_scene["card"]) == pytest.approx(
            _hinge_world(final_card, final_scene["card"]), abs=1e-6
        )

    vertical_prototype = result["cards"][1]["bounds_world_mm"]
    assert vertical_prototype["maximum"][0] - vertical_prototype["minimum"][0] == (
        pytest.approx(63.0, abs=3e-4)
    )
