#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove all via padstacks from a Specctra DSN before autorouting."""

from __future__ import annotations

import argparse
from pathlib import Path


def prepare(source: Path, output: Path) -> None:
    lines = source.read_text(encoding="utf-8").splitlines()
    filtered = [line for line in lines if not line.lstrip().startswith("(via ")]
    text = "\n".join(filtered) + "\n"
    text = text.replace("    (layer B.Cu\n      (type signal)", "    (layer B.Cu\n      (type power)", 1)
    output.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.input, args.output)


if __name__ == "__main__":
    main()
