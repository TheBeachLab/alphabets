# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
import json
import sys
import unittest
from pathlib import Path

VARIANTS_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = VARIANTS_DIR.parents[2]
STICKERS_DIR = REPOSITORY_ROOT / "V2/Hardware/Final/stickers"
for source_dir in (VARIANTS_DIR, STICKERS_DIR):
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

from character_sets import load_presets
from physical_variants import load_variants


class PhysicalVariantTests(unittest.TestCase):
    def test_two_matched_hardware_variants_are_declared(self):
        variants = load_variants()
        self.assertEqual(set(variants), {"prototype", "definitive"})
        self.assertEqual(variants["prototype"].character_preset, "demo-64")
        self.assertEqual(variants["definitive"].character_preset, "international-64")
        self.assertEqual(
            variants["prototype"].enclosure.status, "manufacturing-source"
        )
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
        self.assertEqual(variants["prototype"].sticker.cut_gap_mm, 1.8)
        self.assertEqual(variants["definitive"].sticker.cut_gap_mm, 1.8)
        self.assertEqual(variants["prototype"].sticker.bleed_mm, 2.0)
        self.assertEqual(variants["definitive"].sticker.bleed_mm, 2.0)
        self.assertEqual(variants["definitive"].sticker.artwork_height_mm, 92.8)
        self.assertEqual(
            variants["prototype"].artifacts["sticker_print_cut"],
            "V2/Hardware/Prototype/stickers/cut-print/cutprint.svg",
        )
        self.assertNotIn("sticker_outputs", variants["prototype"].artifacts)
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
        root = REPOSITORY_ROOT
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
        root = REPOSITORY_ROOT
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
                    self.assertEqual(
                        data["geometry_mm"]["cut_gap"],
                        variant.sticker.cut_gap_mm,
                    )
                    self.assertEqual(
                        data["geometry_mm"]["background_bleed"],
                        variant.sticker.bleed_mm,
                    )

    def test_final_sticker_directories_contain_only_current_artifacts(self):
        variant = load_variants()["definitive"]
        generated_dir = REPOSITORY_ROOT / "V2/Hardware/Final/stickers/generated"
        pdf_dir = REPOSITORY_ROOT / "V2/Hardware/Final/stickers/output/pdf"
        expected_generated = {
            Path(path).name
            for path in variant.artifacts["sticker_outputs"]
        }
        expected_generated.update(
            Path(path).with_suffix(".json").name
            for path in variant.artifacts["sticker_outputs"]
        )
        expected_generated.add(Path(variant.artifacts["sticker_cut"]).name)
        self.assertEqual(
            {path.name for path in generated_dir.iterdir() if path.is_file()},
            expected_generated,
        )
        self.assertEqual(
            {path.name for path in pdf_dir.iterdir() if path.is_file()},
            {
                Path(path).name
                for path in variant.artifacts["sticker_pdfs"]
            },
        )
        archive_dir = REPOSITORY_ROOT / "V2/Hardware/Final/stickers/archive"
        self.assertEqual(
            [
                path
                for path in archive_dir.rglob("*")
                if path.is_file() and path.name != ".DS_Store"
            ],
            [],
        )
