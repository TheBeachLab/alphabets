#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Export the enclosure fitted to the saved Blender card positions."""

from __future__ import annotations

import argparse
from pathlib import Path

from alphabets_cad.export import generate_captured_enclosure
from alphabets_cad.parameters import DESIGN, load_design_profile

MECHANICAL_DIR = Path(__file__).resolve().parent
DEFAULT_CAPTURE = (
    MECHANICAL_DIR.parent / "blender/generated/cards-position-capture.json"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--capture",
        type=Path,
        default=DEFAULT_CAPTURE,
        help="settled Blender card-position capture",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=MECHANICAL_DIR / "generated/captured-enclosure",
    )
    parser.add_argument("--profile", type=Path)
    args = parser.parse_args()
    params = load_design_profile(args.profile, base=DESIGN) if args.profile else DESIGN
    generate_captured_enclosure(args.output, args.capture, params)


if __name__ == "__main__":
    main()
