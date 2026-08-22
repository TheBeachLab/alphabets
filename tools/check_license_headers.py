# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Verify explicit copyright and licence declarations for every tracked file."""

from __future__ import annotations

import html
import json
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "V2" / "Code"))

from artifact_license_metadata import (
    SUPPORTED_SUFFIXES as ARTIFACT_SUFFIXES,
)
from artifact_license_metadata import (  # noqa: E402
    ArtifactLicenseMetadataError,
    artifact_suffix,
    validate_artifact_license,
)
from kicad_license_metadata import (
    SUPPORTED_SUFFIXES as KICAD_SUFFIXES,
)
from kicad_license_metadata import (  # noqa: E402
    KiCadLicenseMetadataError,
    validate_kicad_license,
)
from json_license_metadata import (  # noqa: E402
    LicenseMetadataError,
    validate_gerber_job_license,
)

ROOT = Path(__file__).resolve().parents[1]
COMMENTABLE_NAMES = {
    ".gitattributes",
    ".gitignore",
    "Makefile",
    "requirements-vscode.txt",
    "requirements.txt",
}
COMMENTABLE_SUFFIXES = {
    ".bash",
    ".c",
    ".cad",
    ".cc",
    ".cpp",
    ".css",
    ".cxx",
    ".go",
    ".h",
    ".hpp",
    ".ino",
    ".java",
    ".js",
    ".jsx",
    ".ko",
    ".kt",
    ".lua",
    ".make",
    ".md",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".scad",
    ".scss",
    ".sh",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
    ".zsh",
}
HEADER_LINE_LIMIT = 25
COPYRIGHT_MARKER = "SPDX-FileCopyrightText:"
SPDX_LICENSE_PREFIX = "SPDX-License-"
LICENCE_MARKER = f"{SPDX_LICENSE_PREFIX}Identifier:"
JSON_COPYRIGHT_KEY = "SPDX-FileCopyrightText"
JSON_LICENCE_KEY = "SPDX-License-Identifier"
JSON_LIKE_SUFFIXES = {".json", ".code-workspace", ".gbrjob"}
EXPECTED_COPYRIGHT = "2014-2026 The Beach Lab <https://beachlab.org>"
EXPECTED_LICENCE = "MIT"


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [
        path
        for raw_path in result.stdout.split(b"\0")
        if raw_path
        for path in [Path(raw_path.decode())]
        if (ROOT / path).exists()
    ]


def has_spdx_declaration(path: Path) -> bool:
    header = "\n".join(
        (ROOT / path).read_text(errors="replace").splitlines()[:HEADER_LINE_LIMIT]
    )
    return COPYRIGHT_MARKER in header and LICENCE_MARKER in header


def has_adjacent_declaration(path: Path, tracked: set[Path]) -> bool:
    sidecar = Path(f"{path}.license")
    return sidecar in tracked and has_spdx_declaration(sidecar)


def has_embedded_json_declaration(path: Path) -> bool:
    try:
        data = json.loads((ROOT / path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if path.suffix.lower() == ".gbrjob":
        try:
            validate_gerber_job_license(data)
        except LicenseMetadataError:
            return False
        return True
    return (
        isinstance(data, dict)
        and isinstance(data.get(JSON_COPYRIGHT_KEY), str)
        and bool(data[JSON_COPYRIGHT_KEY].strip())
        and isinstance(data.get(JSON_LICENCE_KEY), str)
        and bool(data[JSON_LICENCE_KEY].strip())
    )


def has_embedded_kicad_declaration(path: Path) -> bool:
    try:
        validate_kicad_license(ROOT / path)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        KiCadLicenseMetadataError,
    ):
        return False
    return True


def has_embedded_freecad_declaration(path: Path) -> bool:
    try:
        with zipfile.ZipFile(ROOT / path) as archive:
            document = html.unescape(
                archive.read("Document.xml").decode("utf-8", errors="replace")
            )
    except (OSError, KeyError, zipfile.BadZipFile):
        return False
    return all(
        marker in document
        for marker in (
            "SPDX-FileCopyrightText",
            EXPECTED_COPYRIGHT,
            "SPDX-License-Identifier",
            EXPECTED_LICENCE,
        )
    )


def has_embedded_blend_declaration(path: Path) -> bool:
    try:
        document = (ROOT / path).read_bytes()
    except OSError:
        return False
    return all(
        marker in document
        for marker in (
            b"SPDX-FileCopyrightText",
            EXPECTED_COPYRIGHT.encode(),
            b"SPDX-License-Identifier",
            EXPECTED_LICENCE.encode(),
        )
    )


def _opentype_name_values(path: Path, wanted_ids: set[int]) -> dict[int, set[str]]:
    document = (ROOT / path).read_bytes()
    num_tables = struct.unpack_from(">H", document, 4)[0]
    name_offset = None
    for index in range(num_tables):
        offset = 12 + index * 16
        tag, _, table_offset, _ = struct.unpack_from(">4sIII", document, offset)
        if tag == b"name":
            name_offset = table_offset
            break
    if name_offset is None:
        return {}
    _, count, strings_offset = struct.unpack_from(">HHH", document, name_offset)
    values: dict[int, set[str]] = {}
    for index in range(count):
        record = name_offset + 6 + index * 12
        platform, _, _, name_id, length, offset = struct.unpack_from(
            ">HHHHHH", document, record
        )
        if name_id not in wanted_ids:
            continue
        raw = document[
            name_offset + strings_offset + offset : name_offset
            + strings_offset
            + offset
            + length
        ]
        encoding = "utf-16-be" if platform in {0, 3} else "mac_roman"
        value = raw.decode(encoding, errors="replace").strip()
        if value:
            values.setdefault(name_id, set()).add(value)
    return values


def has_embedded_font_declaration(path: Path) -> bool:
    try:
        values = _opentype_name_values(path, {0, 13, 14})
    except (OSError, IndexError, struct.error):
        return False
    copyright_text = " ".join(values.get(0, ())).lower()
    licence_text = " ".join(values.get(13, ())).lower()
    licence_urls = " ".join(values.get(14, ())).lower()
    return (
        bool(copyright_text)
        and bool(licence_text or licence_urls)
        and any(
            marker in f"{copyright_text} {licence_text} {licence_urls}"
            for marker in ("cc0", "open font license", "ofl")
        )
    )


def has_embedded_native_declaration(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in KICAD_SUFFIXES:
        return has_embedded_kicad_declaration(path)
    if suffix in {".fcstd", ".fcbak"}:
        return has_embedded_freecad_declaration(path)
    if suffix == ".blend":
        return has_embedded_blend_declaration(path)
    if suffix == ".otf":
        return has_embedded_font_declaration(path)
    return False


def has_embedded_artifact_declaration(path: Path) -> bool:
    if artifact_suffix(path) not in ARTIFACT_SUFFIXES:
        return False
    try:
        validate_artifact_license(ROOT / path)
    except (OSError, UnicodeDecodeError, ArtifactLicenseMetadataError):
        return False
    return True


def is_self_describing_license_document(path: Path) -> bool:
    is_license_path = (
        path.name == "LICENSE"
        or path.name.startswith("LICENSE-")
        or (path.parts and path.parts[0] == "LICENSES")
    )
    if not is_license_path:
        return False
    try:
        document = (ROOT / path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    markers = (
        "Apache License",
        "BSD 3-Clause License",
        "Creative Commons",
        "MIT License",
        "OPEN FONT LICENSE",
        "Open Font License",
        "Permission granted for experimental and personal use",
        "Redistribution and use in source and binary forms",
        "Typodermic public-domain font license",
    )
    return any(marker in document for marker in markers)


def requires_inline_declaration(path: Path) -> bool:
    return not path.name.endswith(".license") and (
        path.name in COMMENTABLE_NAMES or path.suffix.lower() in COMMENTABLE_SUFFIXES
    )


def main() -> int:
    paths = tracked_files()
    tracked = set(paths)
    missing = [
        path
        for path in paths
        if not (
            has_embedded_json_declaration(path)
            if path.suffix.lower() in JSON_LIKE_SUFFIXES
            else (
                has_spdx_declaration(path)
                or has_embedded_native_declaration(path)
                or has_embedded_artifact_declaration(path)
                or is_self_describing_license_document(path)
            )
        )
        and (
            requires_inline_declaration(path)
            or not has_adjacent_declaration(path, tracked)
        )
    ]
    orphaned = [
        path
        for path in paths
        if path.name.endswith(".license")
        and Path(str(path)[: -len(".license")]) not in tracked
    ]
    external_json_sidecars = [
        path for path in paths if path.name.endswith(".json.license")
    ]
    redundant_native_sidecars = [
        path
        for path in paths
        if path.name.endswith(".license")
        and (
            has_spdx_declaration(Path(str(path)[: -len(".license")]))
            or has_embedded_native_declaration(Path(str(path)[: -len(".license")]))
            or has_embedded_artifact_declaration(Path(str(path)[: -len(".license")]))
            or is_self_describing_license_document(Path(str(path)[: -len(".license")]))
        )
    ]
    if missing:
        print("Tracked files without copyright and SPDX declarations:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
    if orphaned:
        print("Orphaned .license sidecars:", file=sys.stderr)
        for path in orphaned:
            print(f"  {path}", file=sys.stderr)
    if external_json_sidecars:
        print(
            "JSON files must embed metadata instead of using sidecars:", file=sys.stderr
        )
        for path in external_json_sidecars:
            print(f"  {path}", file=sys.stderr)
    if redundant_native_sidecars:
        print(
            "Native metadata makes these .license sidecars redundant:", file=sys.stderr
        )
        for path in redundant_native_sidecars:
            print(f"  {path}", file=sys.stderr)
    if missing or orphaned or external_json_sidecars or redundant_native_sidecars:
        return 1

    inline_count = sum(requires_inline_declaration(path) for path in paths)
    json_count = sum(path.suffix.lower() in JSON_LIKE_SUFFIXES for path in paths)
    native_count = sum(has_embedded_native_declaration(path) for path in paths)
    artifact_count = sum(has_embedded_artifact_declaration(path) for path in paths)
    license_document_count = sum(
        is_self_describing_license_document(path) for path in paths
    )
    print(
        f"All {len(paths)} tracked files have copyright and SPDX declarations; "
        f"all {inline_count} commentable files use inline headers and all "
        f"{json_count} JSON, {native_count} native documents, and "
        f"{artifact_count} portable artifacts embed metadata; "
        f"{license_document_count} licence texts are self-describing."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
