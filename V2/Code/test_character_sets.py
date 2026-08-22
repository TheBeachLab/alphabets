# SPDX-License-Identifier: MIT
import json
from pathlib import Path
import tempfile
import unittest

from character_sets import (
    CharacterSetError,
    load_catalog,
    load_presets,
    resolve_character_set,
    validate_characters,
)


INTERNATIONAL_64 = " ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜẞÑÇÉÅÆØŁ" "0123456789.,:!?¡¿-/'&@%€$°"
DEMO_64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ:.0123456789$€&@%×/·#=*+-±()<>,\u0027°■£~© "


class CharacterSetTests(unittest.TestCase):
    def setUp(self):
        self.presets = load_presets()

    def test_catalog_has_expected_default_and_presets(self):
        catalog = load_catalog()
        self.assertEqual(catalog["default_preset"], "international-64")
        self.assertEqual(set(self.presets), {"demo-64", "international-64"})

    def test_every_preset_has_64_unique_positions_and_one_space(self):
        for preset in self.presets.values():
            with self.subTest(preset=preset.id):
                self.assertEqual(len(preset.characters), 64)
                self.assertEqual(len(set(preset.characters)), 64)
                self.assertEqual(preset.characters.count(" "), 1)

    def test_international_sequence_is_exact(self):
        self.assertEqual(self.presets["international-64"].characters, INTERNATIONAL_64)

    def test_demo_sequence_preserves_existing_physical_order(self):
        demo = self.presets["demo-64"]
        self.assertEqual(demo.characters, DEMO_64)
        self.assertEqual(demo.characters[0], "A")
        self.assertEqual(demo.characters[39], "€")
        self.assertEqual(demo.characters[63], " ")

    def test_international_normalization_preserves_german_and_common_names(self):
        preset = self.presets["international-64"]
        self.assertEqual(
            preset.normalize_text("Grüße, señor! François 20°"),
            "GRÜẞE, SEÑOR! FRANÇOIS 20°",
        )

    def test_commands_cover_protocol_range(self):
        preset = self.presets["international-64"]
        self.assertEqual(preset.encode_commands(" A°"), [1, 2, 64])
        self.assertTrue(
            all(0x01 <= command <= 0x40 for command in preset.encode_commands("KÖLN"))
        )

    def test_unsupported_character_fails_with_location(self):
        preset = self.presets["international-64"]
        with self.assertRaisesRegex(CharacterSetError, "offset 5"):
            preset.normalize_text("HALLO🙂")

    def test_custom_profile_resolves(self):
        custom_characters = INTERNATIONAL_64[-1] + INTERNATIONAL_64[:-1]
        selected = resolve_character_set(
            {
                "settings_version": 1,
                "character_set": {"name": "My drum", "custom": custom_characters},
            }
        )
        self.assertEqual(selected.id, "custom-64")
        self.assertEqual(selected.name, "My drum")
        self.assertEqual(selected.characters, custom_characters)

    def test_custom_profile_requires_exactly_one_mode(self):
        with self.assertRaisesRegex(CharacterSetError, "exactly one"):
            resolve_character_set(
                {
                    "settings_version": 1,
                    "character_set": {
                        "preset": "international-64",
                        "custom": INTERNATIONAL_64,
                    },
                }
            )

    def test_settings_version_is_required(self):
        with self.assertRaisesRegex(CharacterSetError, "settings_version"):
            resolve_character_set({"character_set": {"preset": "international-64"}})

    def test_unknown_and_wrong_typed_settings_fail(self):
        with self.assertRaisesRegex(CharacterSetError, "unknown settings"):
            resolve_character_set(
                {
                    "settings_version": 1,
                    "character_set": {"preset": "international-64"},
                    "extra": True,
                }
            )
        with self.assertRaisesRegex(CharacterSetError, "must be a boolean"):
            resolve_character_set(
                {
                    "settings_version": 1,
                    "character_set": {
                        "custom": INTERNATIONAL_64,
                        "uppercase_input": "true",
                    },
                }
            )

    def test_duplicate_and_wrong_length_profiles_fail(self):
        with self.assertRaisesRegex(CharacterSetError, "exactly 64"):
            validate_characters(INTERNATIONAL_64[:-1])
        with self.assertRaisesRegex(CharacterSetError, "duplicate"):
            validate_characters(INTERNATIONAL_64[:-1] + "A")

    def test_catalog_validation_rejects_missing_default(self):
        catalog = load_catalog()
        catalog["default_preset"] = "missing"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            with self.assertRaisesRegex(CharacterSetError, "unknown default"):
                load_presets(path)


if __name__ == "__main__":
    unittest.main()
