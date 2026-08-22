#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Import a Freerouting Specctra session into the generated KiCad PCB."""

from __future__ import annotations

import argparse
from pathlib import Path

import pcbnew


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


if __name__ == "__main__":
    main()
