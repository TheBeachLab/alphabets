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
    DEFAULT_FONT,
    DEFAULT_FONT_WEIGHT,
    DEFAULT_FONT_WIDTH,
    FontFace,
    SheetGeometry,
    StickerError,
    build_cut_svg,
    build_svg,
    glyph_placement,
    load_profile,
    main,
    normalize_color,
    resolve_colors,
    select_face,
    typography_layout,
)


SVG = "{http://www.w3.org/2000/svg}"


class StickerGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.faces = [
            FontFace.load(DEFAULT_FONT, DEFAULT_FONT_WEIGHT, DEFAULT_FONT_WIDTH)
        ]
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

    def test_one_font_covers_every_international_character(self):
        for preset in (self.profile, load_profile("demo-64", None)):
            with self.subTest(preset=preset.id):
                unsupported_characters = [
                    character
                    for character in preset.characters
                    if character != " " and not self.faces[0].has(character)
                ]
                self.assertEqual(unsupported_characters, [])
        self.assertEqual(
            self.faces[0].label, "Noto Sans Mono wdth 100 wght 700"
        )

    def test_svg_has_64_cards_63_outlined_glyphs_and_no_text_elements(self):
        svg, positions = build_svg(
            self.profile,
            self.faces,
            SheetGeometry(columns=22),
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
        self.assertTrue(
            all("clip-path" in path.attrib for path in glyphs.findall(f"{SVG}path"))
        )
        self.assertEqual(root.findall(f".//{SVG}text"), [])
        self.assertIsNone(root.find(f"{SVG}g[@id='split-lines']"))
        self.assertEqual(root.attrib["viewBox"], "0 0 1388 278")
        self.assertEqual(len(positions), 64)
        self.assertEqual(
            {position["font"] for position in positions if position["character"] != " "},
            {"Noto Sans Mono wdth 100 wght 700"},
        )

    def test_special_characters_share_scale_advance_and_baseline(self):
        geometry = SheetGeometry(columns=22)
        layout = typography_layout(
            self.profile.characters, self.faces[0], geometry
        )
        placements = [
            glyph_placement(character, self.faces[0], 0, 0, geometry, layout)
            for character in "AÄẞ@€?."
        ]
        self.assertEqual({placement.scale_x for placement in placements}, {layout.scale})
        self.assertEqual({placement.scale_y for placement in placements}, {layout.scale})
        self.assertEqual(
            {placement.baseline_y_mm for placement in placements},
            {layout.baseline_in_card_mm},
        )
        self.assertEqual(
            {round(placement.x_mm, 9) for placement in placements},
            {round((geometry.card_width_mm - layout.advance_mm) / 2, 9)},
        )

    def test_narrow_card_crops_side_space_without_changing_type_alignment(self):
        standard = typography_layout(
            self.profile.characters, self.faces[0], SheetGeometry(card_width_mm=55)
        )
        narrow = typography_layout(
            self.profile.characters, self.faces[0], SheetGeometry(card_width_mm=50)
        )
        self.assertEqual(narrow.scale, standard.scale)
        self.assertEqual(
            narrow.baseline_in_card_mm, standard.baseline_in_card_mm
        )
        self.assertLess(
            SheetGeometry(card_width_mm=50).page_size(64)[0],
            SheetGeometry(card_width_mm=55).page_size(64)[0],
        )

    def test_main_writes_svg_pdf_and_manifest_with_exact_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            svg = root / "sheet.svg"
            pdf = root / "sheet.pdf"
            manifest = root / "sheet.json"
            cut_svg = root / "sheet-cut.svg"
            result = main(
                [
                    "--preset",
                    "international-64",
                    "--color-preset",
                    "black-yellow",
                    "--columns",
                    "22",
                    "--output-svg",
                    str(svg),
                    "--output-pdf",
                    str(pdf),
                    "--output-cut-svg",
                    str(cut_svg),
                    "--manifest",
                    str(manifest),
                ]
            )
            self.assertEqual(result, 0)
            self.assertTrue(svg.read_text(encoding="utf-8").startswith("<?xml"))
            self.assertEqual(pdf.read_bytes()[:4], b"%PDF")
            cut_root = ET.fromstring(cut_svg.read_text(encoding="utf-8"))
            cut_group = cut_root.find(f"{SVG}g[@id='cut-guides']")
            self.assertIsNotNone(cut_group)
            self.assertEqual(len(cut_group.findall(f"{SVG}rect")), 64)
            self.assertEqual(len(cut_group.findall(f"{SVG}path")), 64)
            print_root = ET.fromstring(svg.read_text(encoding="utf-8"))
            self.assertIsNone(print_root.find(f"{SVG}g[@id='cut-guides']"))
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["character_set"]["characters"], self.profile.characters)
            self.assertEqual(data["colors"]["background"], "#000000")
            self.assertEqual(data["colors"]["foreground"], "#FFCC00")
            self.assertIsNone(data["colors"]["guide"])
            self.assertEqual(data["geometry_mm"]["rows"], 3)
            self.assertEqual(len(data["fonts"]), 1)
            self.assertEqual(data["fonts"][0]["family"], "Noto Sans Mono")
            self.assertEqual(
                data["fonts"][0]["variation"], {"wdth": 100.0, "wght": 700.0}
            )
            self.assertEqual(
                data["typography"]["alignment"],
                "monospaced-common-baseline",
            )
            self.assertEqual(len(data["positions"]), 64)

    def test_cut_svg_contains_only_cut_geometry(self):
        cut_svg = build_cut_svg(
            self.profile,
            SheetGeometry(columns=22),
            "#FF00FF",
            False,
        )
        root = ET.fromstring(cut_svg)
        self.assertIsNone(root.find(f"{SVG}g[@id='backgrounds']"))
        self.assertIsNone(root.find(f"{SVG}g[@id='glyphs']"))
        self.assertEqual(len(root.findall(f".//{SVG}rect")), 64)
        self.assertEqual(len(root.findall(f".//{SVG}path")), 64)

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
