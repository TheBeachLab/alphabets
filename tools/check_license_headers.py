#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify that every tracked source file has an explicit licence declaration."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAMES = {"Makefile"}
SOURCE_SUFFIXES = {
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
INLINE_LICENCE_MARKERS = (
    "SPDX-License-Identifier:",
    "Licensed under the Apache License",
    "Released under MIT license",
    "Permission granted for experimental and personal use",
)


def tracked_source_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    paths = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = Path(raw_path.decode())
        if path.name in SOURCE_NAMES or path.suffix.lower() in SOURCE_SUFFIXES:
            paths.append(path)
    return paths


def has_inline_licence(path: Path) -> bool:
    header = "\n".join(
        (ROOT / path).read_text(errors="replace").splitlines()[:HEADER_LINE_LIMIT]
    )
    return any(marker in header for marker in INLINE_LICENCE_MARKERS)


def has_adjacent_third_party_licence(path: Path) -> bool:
    if "third_party" not in path.parts:
        return False

    parent = (ROOT / path).parent
    while parent != ROOT:
        if any(candidate.is_file() for candidate in parent.glob("LICENSE*")):
            return True
        parent = parent.parent
    return False


def main() -> int:
    missing = [
        path
        for path in tracked_source_files()
        if not has_inline_licence(path)
        and not has_adjacent_third_party_licence(path)
    ]
    if missing:
        print("Source files without an explicit licence:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    print("All tracked source files have an explicit licence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
