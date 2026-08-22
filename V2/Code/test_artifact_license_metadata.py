# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
import binascii
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from artifact_license_metadata import (
    DEFAULT_LICENSE_TEXT,
    embed_artifact_license,
    validate_artifact_license,
)


class ArtifactLicenseMetadataTests(unittest.TestCase):
    def round_trip(self, suffix: str, contents: bytes) -> bytes:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"artifact{suffix}"
            path.write_bytes(contents)
            embed_artifact_license(path)
            first = path.read_bytes()
            embed_artifact_license(path)
            self.assertEqual(path.read_bytes(), first)
            validate_artifact_license(path)
            return first

    def test_svg_metadata(self):
        result = self.round_trip(
            ".svg", b'<svg xmlns="http://www.w3.org/2000/svg"></svg>\n'
        )
        self.assertIn(b"alphabets-license", result)

    def test_png_text_chunk(self):
        def chunk(kind: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + kind
                + data
                + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
            )

        png = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IEND", b"")
        )
        self.assertIn(DEFAULT_LICENSE_TEXT.encode(), self.round_trip(".png", png))

    def test_jpeg_comment(self):
        result = self.round_trip(".jpg", b"\xff\xd8\xff\xd9")
        self.assertTrue(result.startswith(b"\xff\xd8\xff\xfe"))

    def test_text_cad_and_fabrication_formats(self):
        samples = {
            ".step": b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n",
            ".dxf": b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n",
            ".gtl": b"%FSLAX46Y46*%\nM02*\n",
            ".drl": b"M48\nM30\n",
        }
        for suffix, contents in samples.items():
            with self.subTest(suffix=suffix):
                result = self.round_trip(suffix, contents)
                if suffix == ".dxf":
                    self.assertTrue(result.startswith(b"0\nSECTION\n2\nHEADER\n"))
                    self.assertGreater(result.index(b"ALPHABETS_LICENSE_BEGIN"), 0)

    def test_dxf_without_header_section(self):
        result = self.round_trip(
            ".dxf", b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n"
        )
        self.assertTrue(result.startswith(b"0\nSECTION\n2\nENTITIES\n999\n"))

    def test_binary_stl_header(self):
        stl = b"original".ljust(80, b" ") + struct.pack("<I", 0)
        result = self.round_trip(".stl", stl)
        self.assertIn(b"The Beach Lab", result[:80])

    def test_zip_archive_comment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("payload.txt", "payload")
            embed_artifact_license(path)
            first = path.read_bytes()
            embed_artifact_license(path)
            self.assertEqual(path.read_bytes(), first)
            validate_artifact_license(path)
            with zipfile.ZipFile(path) as archive:
                self.assertEqual(archive.read("payload.txt"), b"payload")


if __name__ == "__main__":
    unittest.main()
