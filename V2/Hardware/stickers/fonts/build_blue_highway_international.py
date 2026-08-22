#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the Blue Highway D font completed with required Overpass glyphs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from fontTools.misc.transform import Transform
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

FONTS_DIR = Path(__file__).resolve().parent
V2_DIR = FONTS_DIR.parents[2]
DEFAULT_BASE_FONT = FONTS_DIR / "Blue Highway D.otf"
DEFAULT_FALLBACK_FONT = FONTS_DIR / "OverpassMono-Medium.otf"
DEFAULT_OUTPUT_FONT = FONTS_DIR / "BlueHighwayD-International.otf"
DEFAULT_OUTPUT_MANIFEST = FONTS_DIR / "BlueHighwayD-International.json"
DEFAULT_CHARACTER_CATALOG = V2_DIR / "Code" / "character_sets.json"
FAMILY_NAME = "Blue Highway D International"
POSTSCRIPT_NAME = "BlueHighwayD-International"
FONT_EPOCH = 2082844800  # 1970-01-01 in the TrueType/Mac epoch.


class HybridFontError(ValueError):
    """Raised when the hybrid cannot be built safely."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_characters(catalog_path: Path) -> str:
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HybridFontError(
            f"cannot read character catalog: {catalog_path}"
        ) from error
    presets = catalog.get("presets")
    if not isinstance(presets, list):
        raise HybridFontError("character catalog has no presets")
    characters: list[str] = []
    for preset in presets:
        if not isinstance(preset, dict) or not isinstance(
            preset.get("characters"), str
        ):
            raise HybridFontError("character catalog preset is invalid")
        characters.extend(preset["characters"])
    return "".join(dict.fromkeys(characters))


def _make_cff_mutable(font: TTFont) -> Any:
    """Expand indexed CFF charstrings so a new glyph can be appended."""

    top_dict = font["CFF "].cff.topDictIndex[0]
    charstrings = top_dict.CharStrings
    if charstrings.charStringsAreIndexed:
        charstrings.charStrings = {
            glyph_name: charstrings[glyph_name] for glyph_name in charstrings.charStrings
        }
        charstrings.charStringsAreIndexed = 0
        charstrings.private = top_dict.Private
    return top_dict


def _set_name_records(font: TTFont, fallback_characters: str) -> None:
    name = font["name"]
    name.names = [
        record
        for record in name.names
        if record.nameID not in {0, 1, 2, 3, 4, 6, 13, 14, 16, 17}
    ]
    copyright_text = (
        "Blue Highway D components are CC0; added "
        f"{', '.join(f'U+{ord(character):04X}' for character in fallback_characters)} "
        "glyphs are adapted from Overpass Mono Medium under SIL OFL 1.1."
    )
    license_text = (
        "Blue Highway D components are CC0. This font embeds adapted glyphs "
        "from Overpass Mono Medium, licensed under the SIL Open Font License 1.1."
    )
    for platform_id, encoding_id, language_id in ((3, 1, 0x409), (1, 0, 0)):
        name.setName(copyright_text, 0, platform_id, encoding_id, language_id)
        name.setName(FAMILY_NAME, 1, platform_id, encoding_id, language_id)
        name.setName("Regular", 2, platform_id, encoding_id, language_id)
        name.setName(
            f"1.000;HYBR;{POSTSCRIPT_NAME}", 3, platform_id, encoding_id, language_id
        )
        name.setName(FAMILY_NAME, 4, platform_id, encoding_id, language_id)
        name.setName("Version 1.000", 5, platform_id, encoding_id, language_id)
        name.setName(POSTSCRIPT_NAME, 6, platform_id, encoding_id, language_id)
        name.setName(license_text, 13, platform_id, encoding_id, language_id)
        name.setName(
            "https://openfontlicense.org/open-font-license-official-text/",
            14,
            platform_id,
            encoding_id,
            language_id,
        )
        name.setName(FAMILY_NAME, 16, platform_id, encoding_id, language_id)
        name.setName("Regular", 17, platform_id, encoding_id, language_id)


def build_hybrid_font(
    base_path: Path,
    fallback_path: Path,
    output_path: Path,
    characters: str,
) -> dict[str, Any]:
    """Build the hybrid and return its reproducibility manifest."""

    base_path = base_path.resolve()
    fallback_path = fallback_path.resolve()
    output_path = output_path.resolve()
    base = TTFont(base_path)
    fallback = TTFont(fallback_path)
    base_cmap = base.getBestCmap() or {}
    fallback_cmap = fallback.getBestCmap() or {}
    missing = "".join(
        character for character in characters if ord(character) not in base_cmap
    )
    unavailable = "".join(
        character for character in missing if ord(character) not in fallback_cmap
    )
    if unavailable:
        raise HybridFontError(
            f"fallback font lacks required characters: {unavailable!r}"
        )

    top_dict = _make_cff_mutable(base)
    base_upm = base["head"].unitsPerEm
    fallback_upm = fallback["head"].unitsPerEm
    scale = base_upm / fallback_upm
    fallback_glyph_set = fallback.getGlyphSet()
    glyph_order = base.getGlyphOrder()
    added: dict[str, str] = {}

    for character in missing:
        fallback_glyph_name = fallback_cmap[ord(character)]
        hybrid_glyph_name = f"hybrid_{fallback_glyph_name}"
        if hybrid_glyph_name in glyph_order:
            raise HybridFontError(
                f"hybrid glyph name already exists: {hybrid_glyph_name}"
            )
        fallback_advance, fallback_lsb = fallback["hmtx"][fallback_glyph_name]
        pen = T2CharStringPen(
            width=fallback_advance * scale,
            glyphSet=None,
        )
        transformed_pen = TransformPen(pen, Transform(scale, 0, 0, scale, 0, 0))
        fallback_glyph_set[fallback_glyph_name].draw(transformed_pen)
        charstring = pen.getCharString(
            private=top_dict.Private,
            globalSubrs=top_dict.GlobalSubrs,
        )
        top_dict.CharStrings.charStrings[hybrid_glyph_name] = charstring
        top_dict.charset.append(hybrid_glyph_name)
        base["hmtx"].metrics[hybrid_glyph_name] = (
            round(fallback_advance * scale),
            round(fallback_lsb * scale),
        )
        glyph_order.append(hybrid_glyph_name)
        added[character] = hybrid_glyph_name

    base.setGlyphOrder(glyph_order)
    base["maxp"].numGlyphs = len(glyph_order)
    base["hhea"].numberOfHMetrics = len(glyph_order)
    for table in base["cmap"].tables:
        if table.isUnicode():
            table.cmap.update(
                {ord(character): name for character, name in added.items()}
            )
    top_dict.FontName = POSTSCRIPT_NAME
    _set_name_records(base, missing)
    base.recalcTimestamp = False
    base["head"].created = FONT_EPOCH
    base["head"].modified = FONT_EPOCH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)

    output = TTFont(output_path)
    output_cmap = output.getBestCmap() or {}
    remaining = "".join(
        character for character in characters if ord(character) not in output_cmap
    )
    if remaining:
        raise HybridFontError(f"hybrid output lacks required characters: {remaining!r}")
    if output["head"].unitsPerEm != base_upm:
        raise HybridFontError("hybrid output changed the Blue Highway units per em")
    return {
        "schema_version": 1,
        "output": output_path.name,
        "family": FAMILY_NAME,
        "postscript_name": POSTSCRIPT_NAME,
        "base": {"file": base_path.name, "sha256": sha256(base_path)},
        "fallback": {
            "file": fallback_path.name,
            "sha256": sha256(fallback_path),
            "characters": missing,
            "scale_to_base_upm": scale,
        },
        "output_sha256": sha256(output_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE_FONT)
    parser.add_argument("--fallback", type=Path, default=DEFAULT_FALLBACK_FONT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FONT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_OUTPUT_MANIFEST)
    parser.add_argument(
        "--character-catalog", type=Path, default=DEFAULT_CHARACTER_CATALOG
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_hybrid_font(
            args.base,
            args.fallback,
            args.output,
            required_characters(args.character_catalog),
        )
    except (HybridFontError, OSError) as error:
        print(f"error: {error}")
        return 2
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
