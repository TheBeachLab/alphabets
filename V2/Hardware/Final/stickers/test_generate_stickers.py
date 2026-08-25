# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from fontTools.pens.boundsPen import BoundsPen

STICKERS_DIR = Path(__file__).resolve().parent
if str(STICKERS_DIR) not in sys.path:
    sys.path.insert(0, str(STICKERS_DIR))

from generate_stickers import (  # noqa: E402
    COLOR_PRESETS,
    CONDENSED_AE_BOUNDS,
    CONDENSED_AE_PATH,
    CONDENSED_W_PATH,
    DEFAULT_FONT,
    DEFAULT_FONT_WEIGHT,
    DEFAULT_FONT_WIDTH,
    GLYPH_X_SCALE_FACTORS,
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
    typography_layout,
    write_pdf,
)
from json_license_metadata import JSON_LICENSE_METADATA

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
        self.assertEqual(self.faces[0].label, "Blue Highway D International Regular")

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
        glyph_groups = glyphs.findall(f"{SVG}g")
        glyph_paths = glyphs.findall(f".//{SVG}path")
        self.assertEqual(len(glyph_groups), 63)
        self.assertEqual(len(glyph_paths), 63)
        self.assertEqual(glyphs.attrib["fill-rule"], "nonzero")
        self.assertTrue(all("clip-path" in group.attrib for group in glyph_groups))
        self.assertTrue(all("clip-path" not in path.attrib for path in glyph_paths))
        self.assertEqual(root.findall(f".//{SVG}text"), [])
        self.assertIsNone(root.find(f"{SVG}g[@id='split-lines']"))
        self.assertEqual(root.attrib["viewBox"], "0 0 1388 278")
        self.assertEqual(len(positions), 64)
        self.assertEqual(
            {
                position["font"]
                for position in positions
                if position["character"] != " "
            },
            {"Blue Highway D International Regular"},
        )

    def test_special_characters_share_scale_baseline_and_card_center(self):
        geometry = SheetGeometry(columns=22)
        layout = typography_layout(self.profile.characters, self.faces[0], geometry)
        placements = [
            glyph_placement(character, self.faces[0], 0, 0, geometry, layout)
            for character in "AÄẞ@€?."
        ]
        self.assertEqual(
            {placement.scale_x for placement in placements}, {layout.scale_x}
        )
        self.assertEqual(
            {placement.scale_y for placement in placements}, {layout.scale_y}
        )
        self.assertEqual(
            {placement.baseline_y_mm for placement in placements},
            {layout.baseline_in_card_mm},
        )
        self.assertFalse(layout.is_monospaced)
        glyph_set = self.faces[0].glyph_set()
        for placement in placements:
            bounds_pen = BoundsPen(glyph_set)
            glyph_set[placement.glyph_name].draw(bounds_pen)
            self.assertIsNotNone(bounds_pen.bounds)
            x_min, _, x_max, _ = bounds_pen.bounds
            visible_center = placement.x_mm + (x_min + x_max) * layout.scale_x / 2
            self.assertAlmostEqual(visible_center, geometry.card_width_mm / 2)

    def test_w_and_ae_use_condensed_outlines_with_matching_visible_width(self):
        geometry = SheetGeometry(
            card_width_mm=45.0,
            card_height_mm=91.0,
            split_y_mm=45.5,
            cut_gap_mm=1.8,
            use_condensed_overrides=True,
        )
        layout = typography_layout(self.profile.characters, self.faces[0], geometry)
        w = glyph_placement("W", self.faces[0], 0, 0, geometry, layout)
        ae = glyph_placement("Æ", self.faces[0], 0, 0, geometry, layout)
        self.assertEqual(GLYPH_X_SCALE_FACTORS["W"], 0.95902088)
        self.assertEqual(w.path_data, CONDENSED_W_PATH)
        self.assertEqual(ae.path_data, CONDENSED_AE_PATH)
        self.assertAlmostEqual(
            w.scale_x, layout.scale_x * GLYPH_X_SCALE_FACTORS["W"]
        )
        self.assertAlmostEqual(
            ae.scale_x, layout.scale_x * GLYPH_X_SCALE_FACTORS["Æ"]
        )
        self.assertEqual(w.scale_y, layout.scale_y)
        self.assertEqual(ae.scale_y, layout.scale_y)
        self.assertAlmostEqual(555.0 * w.scale_x, 521.0 * ae.scale_x)
        self.assertAlmostEqual(w.x_mm + 555.0 * w.scale_x / 2, 22.5)
        self.assertAlmostEqual(
            ae.x_mm
            + (CONDENSED_AE_BOUNDS[0] + CONDENSED_AE_BOUNDS[2])
            * ae.scale_x
            / 2,
            22.5,
        )

        widest = glyph_placement("%", self.faces[0], 0, 0, geometry, layout)
        glyph_set = self.faces[0].glyph_set()
        bounds_pen = BoundsPen(glyph_set)
        glyph_set[widest.glyph_name].draw(bounds_pen)
        self.assertIsNotNone(bounds_pen.bounds)
        x_min, _, x_max, _ = bounds_pen.bounds
        self.assertAlmostEqual(widest.x_mm + x_min * widest.scale_x, 0.0)
        self.assertAlmostEqual(widest.x_mm + x_max * widest.scale_x, 45.0)

    def test_tall_narrow_card_uses_one_width_driven_uniform_scale(self):
        standard = typography_layout(
            self.profile.characters, self.faces[0], SheetGeometry(card_width_mm=55)
        )
        narrow_geometry = SheetGeometry(card_width_mm=50, card_height_mm=96)
        narrow = typography_layout(
            self.profile.characters, self.faces[0], narrow_geometry
        )
        self.assertLess(narrow.scale_x, standard.scale_x)
        self.assertLess(narrow.scale_y, standard.scale_y)
        self.assertEqual(narrow.scale_x, narrow.scale_y)
        self.assertEqual(standard.scale_x, standard.scale_y)
        self.assertLessEqual(
            narrow.max_visible_width_units * narrow.scale_x,
            narrow_geometry.card_width_mm - 2 * narrow_geometry.glyph_padding_x_mm,
        )
        self.assertEqual(narrow.width_ratio, 1.0)
        self.assertEqual(standard.width_ratio, 1.0)
        self.assertLess(
            narrow_geometry.page_size(64)[0],
            SheetGeometry(card_width_mm=55).page_size(64)[0],
        )

    def test_proportional_font_uses_the_same_centering_model(self):
        face = FontFace.load(STICKERS_DIR / "fonts" / "Blue Highway D.otf")
        geometry = SheetGeometry(columns=4)
        layout = typography_layout("ABMW", face, geometry)
        self.assertFalse(layout.is_monospaced)
        glyph_set = face.glyph_set()
        for character in "ABMW":
            placement = glyph_placement(character, face, 0, 0, geometry, layout)
            bounds_pen = BoundsPen(glyph_set)
            glyph_set[placement.glyph_name].draw(bounds_pen)
            self.assertIsNotNone(bounds_pen.bounds)
            x_min, _, x_max, _ = bounds_pen.bounds
            visible_center = placement.x_mm + (x_min + x_max) * layout.scale_x / 2
            self.assertAlmostEqual(visible_center, geometry.card_width_mm / 2)

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
            self.assertEqual(len(cut_group.findall(f"{SVG}rect")), 128)
            self.assertEqual(len(cut_group.findall(f"{SVG}path")), 0)
            print_root = ET.fromstring(svg.read_text(encoding="utf-8"))
            print_guides = print_root.find(f"{SVG}g[@id='cut-guides']")
            self.assertIsNotNone(print_guides)
            self.assertEqual(len(print_guides.findall(f"{SVG}rect")), 128)
            self.assertEqual(len(print_guides.findall(f"{SVG}path")), 0)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(
                {key: data[key] for key in JSON_LICENSE_METADATA},
                JSON_LICENSE_METADATA,
            )
            self.assertEqual(
                data["character_set"]["characters"], self.profile.characters
            )
            self.assertEqual(data["colors"]["background"], "#000000")
            self.assertEqual(data["colors"]["foreground"], "#FFCC00")
            self.assertEqual(data["colors"]["guide"], "#FF00FF")
            self.assertEqual(data["geometry_mm"]["rows"], 3)
            self.assertEqual(len(data["fonts"]), 1)
            self.assertEqual(data["fonts"][0]["family"], "Blue Highway D International")
            self.assertEqual(data["fonts"][0]["variation"], {})
            self.assertEqual(
                data["typography"]["alignment"],
                "common-transform-baseline-centered-bounds",
            )
            self.assertEqual(data["typography"]["spacing"], "proportional")
            self.assertEqual(len(data["positions"]), 64)

    def test_variant_selects_its_matched_characters_and_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for variant, preset, card in (
                ("prototype", "demo-64", [50.0, 80.0]),
                ("definitive", "international-64", [45.0, 91.0]),
            ):
                with self.subTest(variant=variant):
                    svg = root / f"{variant}.svg"
                    result = main(["--variant", variant, "--output-svg", str(svg)])
                    self.assertEqual(result, 0)
                    data = json.loads(
                        svg.with_suffix(".json").read_text(encoding="utf-8")
                    )
                    self.assertEqual(data["physical_variant"], variant)
                    self.assertEqual(data["character_set"]["id"], preset)
                    self.assertEqual(data["geometry_mm"]["card"], card)
                    self.assertEqual(data["geometry_mm"]["cut_gap"], 1.8)
                    self.assertEqual(
                        data["geometry_mm"]["artwork"],
                        [card[0], card[1] + 1.8],
                    )
                    self.assertEqual(data["typography"]["width_ratio"], 1.0)
                    expected_condensed = {"W"}
                    if variant == "definitive":
                        expected_condensed.add("Æ")
                    self.assertEqual(
                        set(data["typography"]["glyph_x_scale_factors"]),
                        expected_condensed,
                    )
                    self.assertAlmostEqual(
                        data["typography"]["glyph_x_scale_factors"]["W"],
                        0.95902088,
                    )
                    self.assertEqual(
                        data["typography"]["glyph_outline_overrides"]["W"]["family"],
                        "Blue Highway Condensed",
                    )
                    if variant == "definitive":
                        self.assertEqual(
                            data["typography"]["glyph_outline_overrides"]["Æ"][
                                "family"
                            ],
                            "Blue Highway Condensed",
                        )
                    self.assertAlmostEqual(
                        data["typography"]["max_visible_width_mm"], card[0]
                    )

    def test_variant_rejects_incompatible_sticker_dimension(self):
        with tempfile.TemporaryDirectory() as directory:
            svg = Path(directory) / "sheet.svg"
            self.assertEqual(
                main(
                    [
                        "--variant",
                        "definitive",
                        "--card-width",
                        "55",
                        "--output-svg",
                        str(svg),
                    ]
                ),
                2,
            )
            self.assertFalse(svg.exists())

    def test_no_guides_writes_clean_artwork(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            svg = root / "clean.svg"
            manifest = root / "clean.json"
            result = main(
                [
                    "--preset",
                    "international-64",
                    "--no-guides",
                    "--output-svg",
                    str(svg),
                    "--manifest",
                    str(manifest),
                ]
            )
            self.assertEqual(result, 0)
            print_root = ET.fromstring(svg.read_text(encoding="utf-8"))
            self.assertIsNone(print_root.find(f"{SVG}g[@id='cut-guides']"))
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertIsNone(data["colors"]["guide"])

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
        self.assertEqual(len(root.findall(f".//{SVG}rect")), 128)
        self.assertEqual(len(root.findall(f".//{SVG}path")), 0)

    def test_definitive_cut_has_two_45_5_mm_rectangles_with_prototype_gap(self):
        geometry = SheetGeometry(
            card_width_mm=45.0,
            card_height_mm=91.0,
            split_y_mm=45.5,
            cut_gap_mm=1.8,
            columns=1,
        )
        root = ET.fromstring(
            build_cut_svg(self.profile, geometry, "#FF00FF", True)
        )
        rectangles = root.findall(f".//{SVG}rect")[:2]
        self.assertEqual(
            [rectangle.attrib for rectangle in rectangles],
            [
                {"x": "5", "y": "5", "width": "45", "height": "45.5"},
                {"x": "5", "y": "52.3", "width": "45", "height": "45.5"},
            ],
        )

    def test_pdf_glyphs_use_nonzero_winding_fill(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sheet.pdf"
            with patch(
                "generate_stickers.canvas.Canvas.drawPath",
                autospec=True,
            ) as draw_path:
                write_pdf(
                    output,
                    self.profile,
                    self.faces,
                    SheetGeometry(columns=22),
                    "#000000",
                    "#FFFFFF",
                    "#FF00FF",
                    False,
                    False,
                )
            self.assertEqual(draw_path.call_count, 63)
            self.assertTrue(
                all(
                    call.kwargs == {"fill": 1, "stroke": 0, "fillMode": 1}
                    for call in draw_path.call_args_list
                )
            )

    def test_custom_settings_order_is_used(self):
        custom = self.profile.characters[1:] + self.profile.characters[:1]
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "settings.json"
            settings.write_text(
                json.dumps(
                    {
                        **JSON_LICENSE_METADATA,
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
