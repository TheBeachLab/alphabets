# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
import json
import sys
import tempfile
import unittest
from pathlib import Path

from fontTools.ttLib import TTFont

STICKERS_DIR = Path(__file__).resolve().parent
FONTS_DIR = STICKERS_DIR / "fonts"
if str(FONTS_DIR) not in sys.path:
    sys.path.insert(0, str(FONTS_DIR))

from build_blue_highway_international import (
    DEFAULT_BASE_FONT,
    DEFAULT_FALLBACK_FONT,
    DEFAULT_OUTPUT_FONT,
    FAMILY_NAME,
    build_hybrid_font,
    required_characters,
)
from character_sets import load_presets


class BlueHighwayInternationalTests(unittest.TestCase):
    def test_fonts_directory_contains_only_the_production_font_and_its_inputs(self):
        self.assertEqual(
            {path.name for path in FONTS_DIR.iterdir() if path.is_file()},
            {
                "Blue Highway D.otf",
                "BlueHighwayD-International.json",
                "BlueHighwayD-International.otf",
                "LICENSE-CC0.txt",
                "LICENSE-OVERPASS-OFL.txt",
                "OverpassMono-Medium.otf",
                "README.md",
                "build_blue_highway_international.py",
            },
        )

    def test_committed_hybrid_covers_both_physical_character_profiles(self):
        font = TTFont(DEFAULT_OUTPUT_FONT)
        cmap = font.getBestCmap() or {}
        for profile in load_presets().values():
            with self.subTest(profile=profile.id):
                self.assertEqual(
                    "",
                    "".join(
                        character
                        for character in profile.characters
                        if ord(character) not in cmap
                    ),
                )
        self.assertEqual(font["name"].getDebugName(1), FAMILY_NAME)

    def test_only_missing_blue_highway_characters_come_from_overpass(self):
        base = TTFont(DEFAULT_BASE_FONT)
        hybrid = TTFont(DEFAULT_OUTPUT_FONT)
        base_cmap = base.getBestCmap() or {}
        hybrid_cmap = hybrid.getBestCmap() or {}
        required = required_characters(
            STICKERS_DIR / "character_sets.json"
        )
        missing_from_blue = "".join(
            character for character in required if ord(character) not in base_cmap
        )
        self.assertEqual(missing_from_blue, "■ẞ")
        for character in required:
            with self.subTest(character=character):
                if ord(character) in base_cmap:
                    self.assertEqual(
                        hybrid_cmap[ord(character)], base_cmap[ord(character)]
                    )
                else:
                    self.assertNotEqual(hybrid_cmap[ord(character)], ".notdef")

    def test_builder_is_reproducible_and_records_the_two_fallbacks(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "hybrid.otf"
            manifest = build_hybrid_font(
                DEFAULT_BASE_FONT,
                DEFAULT_FALLBACK_FONT,
                output,
                required_characters(
                    STICKERS_DIR / "character_sets.json"
                ),
            )
            committed = json.loads(
                (FONTS_DIR / "BlueHighwayD-International.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(committed["SPDX-License-Identifier"], "MIT")
            self.assertEqual(manifest["fallback"]["characters"], "■ẞ")
            self.assertEqual(manifest["output_sha256"], committed["output_sha256"])
