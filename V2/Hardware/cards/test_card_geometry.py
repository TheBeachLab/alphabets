import json
import math
import re
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


CARDS_DIR = Path(__file__).resolve().parent
REPO_ROOT = CARDS_DIR.parents[2]
SVG = "{http://www.w3.org/2000/svg}"


class CardGeometryTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(
            (CARDS_DIR / "card-50x48.json").read_text(encoding="utf-8")
        )

    def test_card_matches_the_45x91_sticker_halves(self):
        sticker = json.loads(
            (
                REPO_ROOT
                / "V2/Hardware/stickers/generated/international-64-black-white-45x91.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(self.manifest["matching_sticker_mm"], [45.0, 91.0])
        self.assertEqual(sticker["geometry_mm"]["card"], [45.0, 91.0])
        self.assertEqual(
            self.manifest["card_mm"]["tab_start_height"] * 2,
            sticker["geometry_mm"]["card"][1],
        )

    def test_prototype_card_keeps_55x43_outline_with_50x40_stickers(self):
        manifest = json.loads((CARDS_DIR / "card.json").read_text(encoding="utf-8"))
        card = manifest["card_mm"]
        self.assertEqual(manifest["physical_variant"], "prototype")
        self.assertEqual(card["body_width"], 55.0)
        self.assertEqual(card["visible_height"], 43.0)
        self.assertEqual(card["tab_start_height"], 40.0)
        self.assertEqual(card["total_height"], 43.0)
        self.assertEqual(card["overall_width_with_tabs"], 63.0)
        self.assertEqual(card["material_thickness"], 0.5)
        self.assertEqual(card["sticker_width"], 50.0)
        self.assertEqual(card["sticker_face_height"], 40.0)
        self.assertEqual(card["sticker_side_margin"], 2.5)
        self.assertEqual(card["sticker_y_offset"], 3.0)
        self.assertEqual(card["finished_thickness"], 0.7)
        self.assertEqual(manifest["matching_sticker_mm"], [50.0, 80.0])

    def test_tabs_rotate_in_the_drum_holes_and_keep_axial_clearance(self):
        card = self.manifest["card_mm"]
        drum = self.manifest["drum_mm"]
        self.assertEqual(card["body_width"], 50.0)
        self.assertEqual(card["visible_height"], 48.0)
        self.assertEqual(card["tab_start_height"], 45.5)
        self.assertEqual(card["total_height"], 48.0)
        self.assertEqual(card["tab_width"], 4.0)
        self.assertEqual(card["tab_height"], 2.5)
        self.assertEqual(card["material_thickness"], 0.5)
        self.assertEqual(card["sticker_width"], 45.0)
        self.assertEqual(card["sticker_face_height"], 45.5)
        self.assertEqual(card["sticker_side_margin"], 2.5)
        self.assertEqual(card["sticker_y_offset"], 2.5)
        self.assertEqual(card["sticker_face_thickness"], 0.1)
        self.assertEqual(card["finished_thickness"], 0.7)
        self.assertEqual(card["display_color_source"], "sticker")
        self.assertEqual(card["default_display_color"], "#000000")
        self.assertEqual(card["overall_width_with_tabs"], 58.0)
        self.assertEqual(drum["axial_clearance"], 1.0)
        self.assertEqual(drum["inner_width"], 51.0)
        self.assertEqual(drum["side_thickness"], 2.15)
        self.assertEqual(drum["outer_width"], 55.3)
        self.assertEqual(drum["diameter"], 85.0)
        self.assertEqual(drum["positions"], 64)
        self.assertEqual(drum["flap_hole_diameter"], 3.0)
        self.assertAlmostEqual(drum["tab_rotation_radius"], math.hypot(1.25, 0.25))
        self.assertGreaterEqual(drum["tab_radial_clearance"], 0.15)

    def test_svg_has_a_closed_58x48_mm_cut_path_with_visible_margin(self):
        root = ET.parse(CARDS_DIR / "card-50x48-cut.svg").getroot()
        self.assertEqual(root.attrib["width"], "60mm")
        self.assertEqual(root.attrib["height"], "50mm")
        self.assertEqual(root.attrib["viewBox"], "0 0 60 50")
        path = root.find(f"{SVG}path[@id='card-cut']")
        self.assertIsNotNone(path)
        self.assertTrue(path.attrib["d"].endswith(" Z"))
        self.assertEqual(path.attrib["stroke"], "#FF00FF")
        self.assertEqual(path.attrib["fill"], "none")

    def test_dxf_contains_one_closed_eight_vertex_cut_polyline(self):
        dxf = (CARDS_DIR / "card-50x48-cut.dxf").read_text(encoding="ascii")
        self.assertIn("LWPOLYLINE", dxf)
        self.assertRegex(dxf, r"(?m)^90\n8$")
        self.assertRegex(dxf, r"(?m)^70\n1$")
        self.assertEqual(len(re.findall(r"(?m)^10$", dxf)), 8)
        self.assertEqual(len(re.findall(r"(?m)^20$", dxf)), 8)

    def test_fcstd_records_dimensions_and_contains_shapes(self):
        with zipfile.ZipFile(CARDS_DIR / "card-50x48.fcstd") as archive:
            names = set(archive.namelist())
            document = archive.read("Document.xml").decode("utf-8")
        self.assertIn("CutOutline.Shape.brp", names)
        self.assertIn("Card.Shape.brp", names)
        self.assertIn("FinishedCard.Shape.brp", names)
        self.assertIn('alias="body_width"', document)
        self.assertIn('content="=50 mm"', document)
        self.assertIn('alias="total_height"', document)
        self.assertIn('content="=48 mm"', document)
        self.assertIn('alias="drum_inner_width"', document)
        self.assertIn(
            'content="=body_width + axial_clearance" alias="drum_inner_width"',
            document,
        )
        self.assertIn('alias="sticker_face_thickness"', document)
        self.assertIn('alias="sticker_width"', document)
        self.assertIn('alias="sticker_face_height"', document)
        self.assertIn('alias="finished_thickness"', document)
        self.assertIn('name="StickerColor"', document)
        self.assertIn('value="#000000"', document)
        self.assertIn(
            'expression="Parameters.total_height - Parameters.sticker_face_height"',
            document,
        )
        self.assertIn(
            'expression="Parameters.body_width + 2 * Parameters.tab_width"',
            document,
        )

    def test_spool_source_uses_matching_width_and_preserves_64_positions(self):
        source = (REPO_ROOT / "V2/Hardware/structure/spool.scad").read_text(
            encoding="utf-8"
        )
        self.assertRegex(source, r"ncards\s*=\s*64\s*;")
        self.assertRegex(source, r"flap_width\s*=\s*50\s*;")
        self.assertRegex(source, r"axial_clearance\s*=\s*1\s*;")
        self.assertRegex(source, r"d\s*=\s*flap_width\s*\+\s*axial_clearance\s*;")
        self.assertRegex(source, r"sdiam\s*=\s*85\s*;")
        self.assertRegex(source, r"e\s*=\s*2\.15\s*;")
        self.assertIn('part == "assembly"', source)
        dxf = REPO_ROOT / "V2/Hardware/structure/spool-50mm.dxf"
        self.assertGreater(dxf.stat().st_size, 100_000)
        self.assertIn("ENTITIES", dxf.read_text(encoding="ascii"))


if __name__ == "__main__":
    unittest.main()
