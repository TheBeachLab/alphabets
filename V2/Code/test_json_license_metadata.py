# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
import json
import tempfile
import unittest
from pathlib import Path

from json_license_metadata import (
    JSON_LICENSE_METADATA,
    LicenseMetadataError,
    validate_json_license,
    with_json_license,
    write_licensed_json,
)


class JsonLicenseMetadataTests(unittest.TestCase):
    def test_metadata_is_embedded_first(self):
        licensed = with_json_license({"schema_version": 1})
        self.assertEqual(list(licensed)[:2], list(JSON_LICENSE_METADATA))
        validate_json_license(licensed)

    def test_missing_or_conflicting_metadata_fails(self):
        with self.assertRaisesRegex(LicenseMetadataError, "SPDX-License-Identifier"):
            validate_json_license(
                {
                    "SPDX-FileCopyrightText": JSON_LICENSE_METADATA[
                        "SPDX-FileCopyrightText"
                    ]
                }
            )
        with self.assertRaisesRegex(LicenseMetadataError, "cannot replace"):
            with_json_license({"SPDX-License-Identifier": "GPL-3.0-only"})

    def test_writer_round_trips_embedded_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.json"
            write_licensed_json(path, {"schema_version": 1})
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data, {**JSON_LICENSE_METADATA, "schema_version": 1})


if __name__ == "__main__":
    unittest.main()
