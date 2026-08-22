#!/usr/bin/env python3
"""Generate yellow-on-gloss-black artwork for the 5 x 2 HALLO/WELT! scene."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BLENDER_DIR = Path(__file__).resolve().parent
V2_DIR = BLENDER_DIR.parents[1]
OUTPUT_DIR = BLENDER_DIR / "generated/hello-wall"
TEXTURES_DIR = OUTPUT_DIR / "textures"
FONT_PATH = V2_DIR / "Hardware/stickers/fonts/BlueHighwayD-International.otf"
ROWS = ("HALLO", "WELT!")
BACKGROUND_RGB = (2, 3, 4)
LETTER_RGB = (255, 204, 0)
TEXTURE_SIZE = (512, 1024)


def texture_filename(character: str) -> str:
    return "exclamation.png" if character == "!" else f"{character}.png"


def fitted_font(character: str, draw: ImageDraw.ImageDraw) -> ImageFont.FreeTypeFont:
    max_width = TEXTURE_SIZE[0] * 0.84
    max_height = TEXTURE_SIZE[1] * 0.82
    size = 900
    while size > 1:
        font = ImageFont.truetype(str(FONT_PATH), size=size)
        left, top, right, bottom = draw.textbbox((0, 0), character, font=font)
        if right - left <= max_width and bottom - top <= max_height:
            return font
        size -= 4
    raise RuntimeError(f"cannot fit {character!r} into the sticker texture")


def render_character_texture(character: str, path: Path) -> dict[str, object]:
    image = Image.new("RGB", TEXTURE_SIZE, BACKGROUND_RGB)
    draw = ImageDraw.Draw(image)
    font = fitted_font(character, draw)
    left, top, right, bottom = draw.textbbox((0, 0), character, font=font)
    x = (TEXTURE_SIZE[0] - (right - left)) / 2 - left
    y = (TEXTURE_SIZE[1] - (bottom - top)) / 2 - top
    draw.text((round(x), round(y)), character, font=font, fill=LETTER_RGB)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)
    return {
        "character": character,
        "file": str(path.relative_to(OUTPUT_DIR)),
        "size_px": list(TEXTURE_SIZE),
        "font_size_px": font.size,
        "glyph_bounds_px": [left, top, right, bottom],
        "continuous_split_v": 0.5,
    }


def build_manifest() -> dict[str, object]:
    modules = []
    for row_index, row in enumerate(ROWS, start=1):
        for column_index, character in enumerate(row, start=1):
            modules.append(
                {
                    "row": row_index,
                    "column": column_index,
                    "character": character,
                    "texture": f"textures/{texture_filename(character)}",
                }
            )
    return {
        "schema_version": 1,
        "title": "German hello world",
        "spoken_message": "HALLO WELT!",
        "display_rows": list(ROWS),
        "layout": {"rows": 2, "columns": 5, "module_count": 10},
        "electronics_included": False,
        "stickers": {
            "background_rgb": list(BACKGROUND_RGB),
            "letter_rgb": list(LETTER_RGB),
            "finish": "gloss black",
            "font": str(FONT_PATH.relative_to(V2_DIR)),
            "texture_size_px": list(TEXTURE_SIZE),
            "split_v": 0.5,
        },
        "modules": modules,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    texture_records = []
    for character in dict.fromkeys("".join(ROWS)):
        texture_records.append(
            render_character_texture(
                character,
                TEXTURES_DIR / texture_filename(character),
            )
        )
    manifest = build_manifest()
    manifest["textures"] = texture_records
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
