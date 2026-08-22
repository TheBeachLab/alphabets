# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Verify explicit copyright and licence declarations for every tracked file."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMENTABLE_NAMES = {".gitattributes", ".gitignore", "Makefile"}
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


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [
        Path(raw_path.decode()) for raw_path in result.stdout.split(b"\0") if raw_path
    ]


def has_spdx_declaration(path: Path) -> bool:
    header = "\n".join(
        (ROOT / path).read_text(errors="replace").splitlines()[:HEADER_LINE_LIMIT]
    )
    return COPYRIGHT_MARKER in header and LICENCE_MARKER in header


def has_adjacent_declaration(path: Path) -> bool:
    sidecar = Path(f"{path}.license")
    return (ROOT / sidecar).is_file() and has_spdx_declaration(sidecar)


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
        if not has_spdx_declaration(path)
        and (requires_inline_declaration(path) or not has_adjacent_declaration(path))
    ]
    orphaned = [
        path
        for path in paths
        if path.name.endswith(".license")
        and Path(str(path)[: -len(".license")]) not in tracked
    ]
    if missing:
        print("Tracked files without copyright and SPDX declarations:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
    if orphaned:
        print("Orphaned .license sidecars:", file=sys.stderr)
        for path in orphaned:
            print(f"  {path}", file=sys.stderr)
    if missing or orphaned:
        return 1

    inline_count = sum(requires_inline_declaration(path) for path in paths)
    print(
        f"All {len(paths)} tracked files have copyright and SPDX declarations; "
        f"all {inline_count} commentable files use inline headers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
