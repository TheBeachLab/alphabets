# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Embed and validate licence metadata in native KiCad documents."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from json_license_metadata import JSON_LICENSE_METADATA

# REUSE-IgnoreStart
SPDX_COPYRIGHT = JSON_LICENSE_METADATA["SPDX-FileCopyrightText"]
SPDX_LICENSE = JSON_LICENSE_METADATA["SPDX-License-Identifier"]
LICENSE_URL = "https://github.com/TheBeachLab/alphabets/blob/master/LICENSE"
SPDX_COPYRIGHT_COMMENT = "SPDX-FileCopyrightText: " + SPDX_COPYRIGHT
SPDX_LICENSE_COMMENT = "SPDX-License-Identifier: " + SPDX_LICENSE
PROJECT_VARIABLES = {
    "SPDX_FILE_COPYRIGHT_TEXT": SPDX_COPYRIGHT,
    "SPDX_LICENSE_IDENTIFIER": SPDX_LICENSE,
    "LICENSE_URL": LICENSE_URL,
}
SUPPORTED_SUFFIXES = {
    ".kicad_mod",
    ".kicad_pcb",
    ".kicad_pro",
    ".kicad_sch",
    ".kicad_sym",
}


class KiCadLicenseMetadataError(ValueError):
    """Raised when a KiCad document lacks the expected metadata."""


def _matching_paren(text: str, start: int) -> int:
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    raise KiCadLicenseMetadataError("unbalanced KiCad s-expression")


def _replace_or_add_title_block(text: str) -> str:
    entries = (
        f'\t\t(comment 8 "{SPDX_COPYRIGHT_COMMENT}")',
        f'\t\t(comment 9 "{SPDX_LICENSE_COMMENT}")',
    )
    title = re.search(r"^(?P<indent>[ \t]+)\(title_block", text, re.MULTILINE)
    if title is None:
        paper = re.search(r"^(?P<indent>[ \t]+)\(paper [^\n]+\)$", text, re.MULTILINE)
        if paper is None:
            raise KiCadLicenseMetadataError(
                "KiCad document has no title block or paper section"
            )
        indent = paper.group("indent")
        block = f"\n{indent}(title_block\n" + "\n".join(entries) + f"\n{indent})"
        return text[: paper.end()] + block + text[paper.end() :]

    start = title.start()
    indent = title.group("indent")
    end = _matching_paren(text, start)
    block = text[start : end + 1]
    block = re.sub(r"^[ \t]+\(comment (?:8|9) .*\)\n?", "", block, flags=re.MULTILINE)
    block = block[:-1].rstrip() + "\n" + "\n".join(entries) + f"\n{indent})"
    return text[:start] + block + text[end + 1 :]


def _replace_root_properties(text: str, root_token: str) -> str:
    properties = (
        f'\t(property "SPDX-FileCopyrightText" "{SPDX_COPYRIGHT}")',
        f'\t(property "SPDX-License-Identifier" "{SPDX_LICENSE}")',
        f'\t(property "LicenseURL" "{LICENSE_URL}")',
    )
    for key in ("SPDX-FileCopyrightText", "SPDX-License-Identifier", "LicenseURL"):
        text = re.sub(
            rf'^\t\(property "{re.escape(key)}" .*\)\n?', "", text, flags=re.MULTILINE
        )
    header = re.search(rf"^\({re.escape(root_token)}[^\n]*\n", text)
    if header is None:
        raise KiCadLicenseMetadataError(f"not a {root_token} document")
    return text[: header.end()] + "\n".join(properties) + "\n" + text[header.end() :]


def _top_level_symbol_blocks(text: str) -> list[tuple[int, int]]:
    blocks = []
    for match in re.finditer(r'^(?:\t|  )\(symbol "', text, re.MULTILINE):
        blocks.append((match.start(), _matching_paren(text, match.start()) + 1))
    return blocks


def _replace_symbol_properties(text: str) -> str:
    blocks = _top_level_symbol_blocks(text)
    if not blocks:
        raise KiCadLicenseMetadataError("symbol library has no top-level symbols")
    snippets = (
        (
            f'\t\t(property "SPDX-FileCopyrightText" "{SPDX_COPYRIGHT}"\n'
            "\t\t\t(at 0 0 0)\n"
            "\t\t\t(effects (font (size 1.27 1.27)) hide)\n"
            "\t\t)"
        ),
        (
            f'\t\t(property "SPDX-License-Identifier" "{SPDX_LICENSE}"\n'
            "\t\t\t(at 0 0 0)\n"
            "\t\t\t(effects (font (size 1.27 1.27)) hide)\n"
            "\t\t)"
        ),
        (
            f'\t\t(property "LicenseURL" "{LICENSE_URL}"\n'
            "\t\t\t(at 0 0 0)\n"
            "\t\t\t(effects (font (size 1.27 1.27)) hide)\n"
            "\t\t)"
        ),
    )
    for start, end in reversed(blocks):
        block = text[start:end]
        for key in ("SPDX-FileCopyrightText", "SPDX-License-Identifier", "LicenseURL"):
            property_start = re.search(
                rf'^[ \t]+\(property "{re.escape(key)}" ', block, re.MULTILINE
            )
            if property_start:
                property_end = _matching_paren(block, property_start.start()) + 1
                block = block[: property_start.start()] + block[property_end:].lstrip(
                    "\n"
                )
        anchor = re.search(r"\(on_board (?:yes|no)\)\n", block)
        if anchor is None:
            raise KiCadLicenseMetadataError("top-level symbol has no on_board field")
        block = (
            block[: anchor.end()] + "\n".join(snippets) + "\n" + block[anchor.end() :]
        )
        text = text[:start] + block + text[end:]
    return text


def embed_kicad_license(path: Path) -> None:
    """Embed native metadata in one supported KiCad file."""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise KiCadLicenseMetadataError(f"unsupported KiCad file: {path}")
    if suffix == ".kicad_pro":
        data = json.loads(path.read_text(encoding="utf-8"))
        variables = data.setdefault("text_variables", {})
        variables.update(PROJECT_VARIABLES)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return

    text = path.read_text(encoding="utf-8")
    if suffix == ".kicad_pcb":
        text = _replace_root_properties(text, "kicad_pcb")
        text = _replace_or_add_title_block(text)
    elif suffix == ".kicad_sch":
        text = _replace_or_add_title_block(text)
    elif suffix == ".kicad_mod":
        text = _replace_root_properties(text, "footprint")
    elif suffix == ".kicad_sym":
        text = _replace_symbol_properties(text)
    path.write_text(text, encoding="utf-8")


def validate_kicad_license(path: Path) -> None:
    """Require exact embedded metadata in one supported KiCad file."""
    suffix = path.suffix.lower()
    if suffix == ".kicad_pro":
        data = json.loads(path.read_text(encoding="utf-8"))
        actual = data.get("text_variables", {})
        for key, expected in PROJECT_VARIABLES.items():
            if actual.get(key) != expected:
                raise KiCadLicenseMetadataError(f"{path}: invalid or missing {key}")
        return

    text = path.read_text(encoding="utf-8")
    expected = {
        "SPDX-FileCopyrightText": SPDX_COPYRIGHT,
        "SPDX-License-Identifier": SPDX_LICENSE,
    }
    if suffix == ".kicad_sym":
        blocks = _top_level_symbol_blocks(text)
        if not blocks:
            raise KiCadLicenseMetadataError(f"{path}: no top-level symbols")
        for index, (start, end) in enumerate(blocks, start=1):
            block = text[start:end]
            for key, value in expected.items():
                if f'(property "{key}" "{value}"' not in block:
                    raise KiCadLicenseMetadataError(
                        f"{path}: symbol {index} is missing {key}"
                    )
        return

    if suffix == ".kicad_sch":
        declarations = [
            f'(comment 8 "{SPDX_COPYRIGHT_COMMENT}")',
            f'(comment 9 "{SPDX_LICENSE_COMMENT}")',
        ]
    elif suffix in {".kicad_pcb", ".kicad_mod"}:
        declarations = [
            f'(property "{key}" "{value}")' for key, value in expected.items()
        ]
        if suffix == ".kicad_pcb":
            declarations.extend(
                [
                    f'(comment 8 "{SPDX_COPYRIGHT_COMMENT}")',
                    f'(comment 9 "{SPDX_LICENSE_COMMENT}")',
                ]
            )
    else:
        raise KiCadLicenseMetadataError(f"unsupported KiCad file: {path}")
    for declaration in declarations:
        if declaration not in text:
            raise KiCadLicenseMetadataError(f"{path}: missing {declaration}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path in args.paths:
        if args.check:
            validate_kicad_license(path)
        else:
            embed_kicad_license(path)


if __name__ == "__main__":
    main()
# REUSE-IgnoreEnd
