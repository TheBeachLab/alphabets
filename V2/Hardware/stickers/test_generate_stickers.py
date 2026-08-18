import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


STICKERS_DIR = Path(__file__).resolve().parent
if str(STICKERS_DIR) not in sys.path:
    sys.path.insert(0, str(STICKERS_DIR))

from generate_stickers import (  # noqa: E402
    COLOR_PRESETS,
    DEFAULT_FALLBACK_FONTS,
    DEFAULT_FONT,
    FontFace,
    SheetGeometry,
    StickerError,
    build_svg,
    load_profile,
    main,
    normalize_color,
    resolve_colors,
    select_face,
)


SVG = "{http://www.w3.org/2000/svg}"


class StickerGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.faces = [FontFace.load(DEFAULT_FONT), FontFace.load(DEFAULT_FALLBACK_FONTS[0])]
        cls.profile = load_profile("international-64", None)

    def test_color_presets_and_default(self):
        self.assertEqual(resolve_colors(), ("#000000", "#FFFFFF"))
        self.assertEqual(
            COLOR_PRESETS,
            {
                "black-white": ("#000000", "#FFFFFF"),
                "black-yellow": ("#000000", "#FFCC00"),
                "yellow-black": ("#FFCC00", "#000000"),
                "white-black": ("#FFFFFF", "#000000"),
            },
        )
        self.assertEqual(
            resolve_colors("yellow-black", "#123abc", "#abcdef"),
            ("#123ABC", "#ABCDEF"),
        )

    def test_invalid_color_is_rejected(self):
        for color in ("black", "fff", "#FFFF", "#GG0000"):
            with self.subTest(color=color):
                with self.assertRaisesRegex(StickerError, "#RRGGBB"):
                    normalize_color(color)

    def test_only_sharp_s_uses_fallback_in_international_profile(self):
        fallback_characters = [
            character
            for character in self.profile.characters
            if character != " " and select_face(character, self.faces) is self.faces[1]
        ]
        self.assertEqual(fallback_characters, ["ẞ"])

    def test_svg_has_64_cards_63_outlined_glyphs_and_no_text_elements(self):
        svg, positions = build_svg(
            self.profile,
            self.faces,
            SheetGeometry(columns=8),
            "#000000",
            "#FFFFFF",
            "#FF00FF",
            True,
            False,
        )
        root = ET.fromstring(svg)
        backgrounds = root.find(f"{SVG}g[@id='backgrounds']")
        glyphs = root.find(f"{SVG}g[@id='glyphs']")
        self.assertIsNotNone(backgrounds)
        self.assertIsNotNone(glyphs)
        self.assertEqual(len(backgrounds.findall(f"{SVG}rect")), 64)
        self.assertEqual(len(glyphs.findall(f"{SVG}path")), 63)
        self.assertEqual(root.findall(f".//{SVG}text"), [])
        self.assertEqual(root.attrib["viewBox"], "0 0 478 726")
        self.assertEqual(len(positions), 64)
        sharp_s = next(position for position in positions if position["character"] == "ẞ")
        self.assertEqual(sharp_s["font"], "Dream Orphans Bold")

    def test_main_writes_svg_pdf_and_manifest_with_exact_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            svg = root / "sheet.svg"
            pdf = root / "sheet.pdf"
            manifest = root / "sheet.json"
            result = main(
                [
                    "--preset",
                    "international-64",
                    "--color-preset",
                    "black-yellow",
                    "--columns",
                    "8",
                    "--output-svg",
                    str(svg),
                    "--output-pdf",
                    str(pdf),
                    "--manifest",
                    str(manifest),
                ]
            )
            self.assertEqual(result, 0)
            self.assertTrue(svg.read_text(encoding="utf-8").startswith("<?xml"))
            self.assertEqual(pdf.read_bytes()[:4], b"%PDF")
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["character_set"]["characters"], self.profile.characters)
            self.assertEqual(data["colors"]["background"], "#000000")
            self.assertEqual(data["colors"]["foreground"], "#FFCC00")
            self.assertEqual(data["geometry_mm"]["rows"], 8)
            self.assertEqual(len(data["positions"]), 64)

    def test_custom_settings_order_is_used(self):
        custom = self.profile.characters[1:] + self.profile.characters[:1]
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "settings.json"
            settings.write_text(
                json.dumps(
                    {
                        "settings_version": 1,
                        "character_set": {"name": "Rotated", "custom": custom},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            selected = load_profile(None, settings)
            self.assertEqual(selected.name, "Rotated")
            self.assertEqual(selected.characters, custom)


if __name__ == "__main__":
    unittest.main()
