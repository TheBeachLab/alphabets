# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT

from __future__ import annotations

from generate_hello_wall_assets import (
    BACKGROUND_RGB,
    LETTER_RGB,
    ROWS,
    build_manifest,
)


def test_german_message_fits_the_requested_five_by_two_wall() -> None:
    manifest = build_manifest()
    assert ROWS == ("HALLO", "WELT!")
    assert manifest["spoken_message"] == "HALLO WELT!"
    assert manifest["layout"] == {"rows": 2, "columns": 5, "module_count": 10}
    assert [item["character"] for item in manifest["modules"]] == list("HALLOWELT!")
    assert manifest["electronics_included"] is False
    assert manifest["motor_included"] is True
    assert manifest["scene_kind"] == "technical assembly; no render generated"
    assert manifest["per_module"] == {
        "enclosure_halves": 2,
        "drum_components": 4,
        "cards": 64,
        "stickers": 128,
        "definitive_pawls": 1,
        "motor_components": 4,
        "m3_screws": 4,
        "m3_screw_objects": 16,
        "magnets": 6,
    }
    assert manifest["display_pair"] == {
        "lower": "sticker_37_front",
        "upper": "sticker_38_back",
        "reason": "captured controller display position 37",
    }


def test_sticker_assets_are_gloss_black_with_yellow_letters() -> None:
    manifest = build_manifest()
    assert manifest["stickers"]["background_rgb"] == list(BACKGROUND_RGB)
    assert manifest["stickers"]["letter_rgb"] == list(LETTER_RGB)
    assert manifest["stickers"]["finish"] == "gloss black"
    assert manifest["stickers"]["all_128_faces_mapped"] is True
    assert (
        manifest["stickers"]["base_atlas"]
        == "V2/Final/generated/blender/sticker-atlas.png"
    )
    assert (
        manifest["stickers"]["typography"]
        == "production atlas with independent X/Y fit"
    )
    w = next(module for module in manifest["modules"] if module["character"] == "W")
    o = next(module for module in manifest["modules"] if module["character"] == "O")
    assert w["production_atlas_uv"]["lower"]["character_index"] == 23
    assert o["production_atlas_uv"]["lower"]["character_index"] == 15


def test_fasteners_and_magnets_come_from_the_cad_layout() -> None:
    manifest = build_manifest()
    assert [item["name"] for item in manifest["fasteners"]] == [
        "pawl",
        "axle",
        "motor_negative_y",
        "motor_positive_y",
    ]
    assert len(manifest["magnets"]["placements"]) == 6
    assert manifest["magnets"]["diameter_mm"] == 3.0
    assert manifest["magnets"]["thickness_mm"] == 1.0
    assert manifest["magnets"]["pocket_diameter_mm"] == 3.4
