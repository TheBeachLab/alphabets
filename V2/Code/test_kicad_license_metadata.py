# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
import json
import tempfile
import unittest
from pathlib import Path

from kicad_license_metadata import (
    PROJECT_VARIABLES,
    SPDX_COPYRIGHT,
    SPDX_COPYRIGHT_COMMENT,
    SPDX_LICENSE_COMMENT,
    embed_kicad_license,
    validate_kicad_license,
)


class KiCadLicenseMetadataTests(unittest.TestCase):
    def round_trip(self, suffix: str, contents: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"document{suffix}"
            path.write_text(contents, encoding="utf-8")
            embed_kicad_license(path)
            first = path.read_text(encoding="utf-8")
            embed_kicad_license(path)
            self.assertEqual(path.read_text(encoding="utf-8"), first)
            validate_kicad_license(path)
            return first

    def test_project_variables_are_embedded(self):
        text = self.round_trip(".kicad_pro", '{"meta": {}, "text_variables": {}}\n')
        self.assertEqual(json.loads(text)["text_variables"], PROJECT_VARIABLES)

    def test_board_properties_and_title_block_are_embedded(self):
        text = self.round_trip(
            ".kicad_pcb",
            '(kicad_pcb\n\t(version 20260101)\n\t(paper "A4")\n)\n',
        )
        self.assertIn(f'(property "SPDX-FileCopyrightText" "{SPDX_COPYRIGHT}")', text)
        self.assertIn(f'(comment 9 "{SPDX_LICENSE_COMMENT}")', text)

    def test_schematic_title_block_is_embedded(self):
        text = self.round_trip(
            ".kicad_sch",
            '(kicad_sch\n\t(version 20260101)\n\t(paper "A4")\n)\n',
        )
        self.assertIn(f'(comment 8 "{SPDX_COPYRIGHT_COMMENT}")', text)

    def test_footprint_properties_are_embedded(self):
        text = self.round_trip(
            ".kicad_mod",
            '(footprint "Example"\n\t(version 20240108)\n)\n',
        )
        self.assertIn('(property "SPDX-License-Identifier" "MIT")', text)

    def test_every_symbol_gets_hidden_properties(self):
        text = self.round_trip(
            ".kicad_sym",
            "(kicad_symbol_lib\n\t(version 20260101)\n"
            '\t(symbol "A"\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t)\n'
            '\t(symbol "B"\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t)\n)\n',
        )
        self.assertEqual(text.count('(property "SPDX-License-Identifier" "MIT"'), 2)


if __name__ == "__main__":
    unittest.main()
