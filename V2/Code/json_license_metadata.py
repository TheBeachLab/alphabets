# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Shared embedded licence metadata for Alphabets JSON documents."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SPDX_FILE_COPYRIGHT_TEXT = "2014-2026 The Beach Lab <https://beachlab.org>"
SPDX_LICENSE_IDENTIFIER = "MIT"
JSON_LICENSE_METADATA = {
    "SPDX-FileCopyrightText": SPDX_FILE_COPYRIGHT_TEXT,
    "SPDX-License-Identifier": SPDX_LICENSE_IDENTIFIER,
}
GERBER_JOB_LICENSE_BEGIN = "ALPHABETS_LICENSE_BEGIN"
GERBER_JOB_LICENSE_END = "ALPHABETS_LICENSE_END"
GERBER_JOB_LICENSE_COMMENT = "\n".join(
    (
        GERBER_JOB_LICENSE_BEGIN,
        *(f"{key}: {value}" for key, value in JSON_LICENSE_METADATA.items()),
        GERBER_JOB_LICENSE_END,
    )
)


class LicenseMetadataError(ValueError):
    """Raised when embedded JSON licence metadata is missing or inconsistent."""


def validate_json_license(data: Mapping[str, Any], context: str = "JSON") -> None:
    """Require the canonical project copyright and licence fields."""
    for key, expected in JSON_LICENSE_METADATA.items():
        actual = data.get(key)
        if actual != expected:
            raise LicenseMetadataError(
                f"{context}.{key} must be {expected!r}; got {actual!r}"
            )


def with_json_license(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return data with canonical licence fields first in document order."""
    for key, expected in JSON_LICENSE_METADATA.items():
        if key in data and data[key] != expected:
            raise LicenseMetadataError(
                f"cannot replace {key}={data[key]!r} with {expected!r}"
            )
    return {**JSON_LICENSE_METADATA, **data}


def with_gerber_job_license(data: Mapping[str, Any]) -> dict[str, Any]:
    """Embed SPDX data in the schema-defined Gerber Job Header.Comment field."""
    header_value = data.get("Header")
    if not isinstance(header_value, Mapping):
        raise LicenseMetadataError("Gerber Job Header must be an object")
    header = dict(header_value)
    comment = header.get("Comment", "")
    if not isinstance(comment, str):
        raise LicenseMetadataError("Gerber Job Header.Comment must be a string")
    comment = re.sub(
        rf"(?:\n\n)?{GERBER_JOB_LICENSE_BEGIN}\n.*?\n{GERBER_JOB_LICENSE_END}",
        "",
        comment,
        flags=re.DOTALL,
    ).rstrip()
    header["Comment"] = (
        f"{comment}\n\n{GERBER_JOB_LICENSE_COMMENT}"
        if comment
        else GERBER_JOB_LICENSE_COMMENT
    )
    return {**data, "Header": header}


def validate_gerber_job_license(data: Mapping[str, Any]) -> None:
    """Require canonical SPDX data inside Gerber Job Header.Comment."""
    header = data.get("Header")
    comment = header.get("Comment") if isinstance(header, Mapping) else None
    if not isinstance(comment, str):
        raise LicenseMetadataError("Gerber Job Header.Comment must contain SPDX data")
    for key, expected in JSON_LICENSE_METADATA.items():
        declaration = f"{key}: {expected}"
        if declaration not in comment:
            raise LicenseMetadataError(
                f"Gerber Job Header.Comment must contain {declaration!r}"
            )


def write_licensed_json(
    path: Path,
    data: Mapping[str, Any],
    *,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
) -> None:
    """Write a deterministic JSON object with embedded licence metadata."""
    licensed_data = (
        with_gerber_job_license(data)
        if path.suffix.lower() == ".gbrjob"
        else with_json_license(data)
    )
    path.write_text(
        json.dumps(
            licensed_data,
            ensure_ascii=ensure_ascii,
            indent=2,
            sort_keys=sort_keys,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Embed canonical Alphabets licence metadata in JSON files."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)

    for path in args.paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise LicenseMetadataError(f"{path} must contain a top-level object")
        write_licensed_json(path, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
