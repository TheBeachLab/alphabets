# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
import json
import sys
import unittest
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from character_sets import load_presets
from physical_variants import load_variants


class PhysicalVariantTests(unittest.TestCase):
    def test_two_matched_hardware_variants_are_declared(self):
        variants = load_variants()
        self.assertEqual(set(variants), {"prototype", "definitive"})
        self.assertEqual(variants["prototype"].character_preset, "demo-64")
        self.assertEqual(variants["definitive"].character_preset, "international-64")
        self.assertEqual(variants["prototype"].enclosure.status, "manufacturing-source")
        self.assertEqual(
            variants["definitive"].enclosure.status, "manufacturing-source"
        )
        self.assertEqual(variants["definitive"].card.material_thickness_mm, 0.5)
        self.assertEqual(variants["definitive"].card.sticker_face_thickness_mm, 0.1)
        self.assertEqual(variants["definitive"].card.finished_thickness_mm, 0.7)
        self.assertEqual(variants["prototype"].card.material_thickness_mm, 0.5)
        self.assertEqual(variants["prototype"].sticker.width_mm, 50.0)
        self.assertEqual(variants["prototype"].sticker.face_height_mm, 40.0)
        self.assertEqual(variants["definitive"].sticker.width_mm, 45.0)
        self.assertEqual(variants["definitive"].sticker.face_height_mm, 45.5)
        for variant in variants.values():
            with self.subTest(variant=variant.id):
                self.assertEqual(
                    variant.card.sticker_side_margin_mm(variant.sticker), 2.5
                )
                self.assertEqual(
                    variant.card.visible_height_mm, variant.card.total_height_mm
                )
                self.assertEqual(
                    variant.sticker.height_mm,
                    2 * (variant.card.total_height_mm - variant.card.tab_height_mm),
                )
                self.assertEqual(
                    variant.sticker.split_y_mm,
                    variant.card.total_height_mm - variant.card.tab_height_mm,
                )
                self.assertEqual(variant.drum.positions, 64)

    def test_variant_character_presets_and_declared_sources_exist(self):
        root = CODE_DIR.parents[1]
        presets = load_presets()
        for variant in load_variants().values():
            with self.subTest(variant=variant.id):
                self.assertIn(variant.character_preset, presets)
                self.assertTrue((root / variant.enclosure.source).exists())
                for value in variant.artifacts.values():
                    paths = value if isinstance(value, list) else [value]
                    for path in paths:
                        self.assertTrue((root / path).exists(), path)

    def test_generated_sticker_manifests_carry_their_physical_variant(self):
        root = CODE_DIR.parents[1]
        for variant in load_variants().values():
            for svg_path in variant.artifacts.get("sticker_outputs", []):
                with self.subTest(variant=variant.id, svg_path=svg_path):
                    manifest_path = root / Path(svg_path).with_suffix(".json")
                    data = json.loads(manifest_path.read_text(encoding="utf-8"))
                    self.assertEqual(data["physical_variant"], variant.id)
                    self.assertEqual(
                        data["character_set"]["id"], variant.character_preset
                    )
                    self.assertEqual(
                        data["geometry_mm"]["card"],
                        [variant.sticker.width_mm, variant.sticker.height_mm],
                    )
