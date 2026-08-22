#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Import a Freerouting Specctra session into the generated KiCad PCB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pcbnew

CODE_DIR = Path(__file__).resolve().parents[4] / "Code"
sys.path.insert(0, str(CODE_DIR))

from kicad_license_metadata import embed_kicad_license  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, required=True)
    parser.add_argument("--session", type=Path, required=True)
    args = parser.parse_args()

    board = pcbnew.LoadBoard(str(args.board))
    if not pcbnew.ImportSpecctraSES(board, str(args.session)):
        raise RuntimeError(f"Could not import {args.session}")
    if not pcbnew.SaveBoard(str(args.board), board):
        raise RuntimeError(f"Could not save {args.board}")
    embed_kicad_license(args.board)


if __name__ == "__main__":
    main()
