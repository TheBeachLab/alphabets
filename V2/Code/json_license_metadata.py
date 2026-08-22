# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Shared embedded licence metadata for Alphabets JSON documents."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SPDX_FILE_COPYRIGHT_TEXT = "2014-2026 The Beach Lab <https://beachlab.org>"
SPDX_LICENSE_IDENTIFIER = "MIT"
JSON_LICENSE_METADATA = {
    "SPDX-FileCopyrightText": SPDX_FILE_COPYRIGHT_TEXT,
    "SPDX-License-Identifier": SPDX_LICENSE_IDENTIFIER,
}


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


def write_licensed_json(
    path: Path,
    data: Mapping[str, Any],
    *,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
) -> None:
    """Write a deterministic JSON object with embedded licence metadata."""
    path.write_text(
        json.dumps(
            with_json_license(data),
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
