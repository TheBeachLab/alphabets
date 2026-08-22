from __future__ import annotations

from generate_hello_wall_assets import (
    BACKGROUND_RGB,
    LETTER_RGB,
    ROWS,
    TEXTURE_SIZE,
    build_manifest,
    texture_filename,
)


def test_german_message_fits_the_requested_five_by_two_wall() -> None:
    manifest = build_manifest()
    assert ROWS == ("HALLO", "WELT!")
    assert manifest["spoken_message"] == "HALLO WELT!"
    assert manifest["layout"] == {"rows": 2, "columns": 5, "module_count": 10}
    assert [item["character"] for item in manifest["modules"]] == list("HALLOWELT!")
    assert manifest["electronics_included"] is False


def test_sticker_assets_are_gloss_black_with_yellow_letters() -> None:
    manifest = build_manifest()
    assert manifest["stickers"]["background_rgb"] == list(BACKGROUND_RGB)
    assert manifest["stickers"]["letter_rgb"] == list(LETTER_RGB)
    assert manifest["stickers"]["finish"] == "gloss black"
    assert manifest["stickers"]["texture_size_px"] == list(TEXTURE_SIZE)
    assert manifest["stickers"]["split_v"] == 0.5
    assert texture_filename("!") == "exclamation.png"
