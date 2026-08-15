#!/usr/bin/env python3
"""Check the electrical and mechanical invariants of the V2 module PCB."""

from __future__ import annotations

import argparse
from pathlib import Path

import pcbnew


EXPECTED_PINS = {
    "J1": {"1": "+5V", "2": "GND", "3": "CLOCK", "4": "LATCH", "5": "DATA_IN", "6": "RETURN"},
    "J2": {"1": "+5V", "2": "GND", "3": "CLOCK", "4": "LATCH", "5": "DATA_OUT", "6": "RETURN"},
    "J3": {"1": "COIL_A", "2": "COIL_B", "3": "COIL_C", "4": "COIL_D", "5": "+5V"},
    "J4": {"1": "+5V", "2": "GND", "3": "HOME"},
    "J5": {"1": "DATA_OUT", "2": "+5V", "3": "CLOCK", "4": "DATA_IN", "5": "RESET", "6": "GND"},
    "J6": {"1": "+5V", "2": "GND"},
    "U1": {"1": "+5V", "2": "PB0", "3": "PB1", "4": "RESET", "5": "HOME", "6": "LATCH", "7": "DATA_IN", "8": "DATA_OUT", "9": "CLOCK", "10": "MOTOR4", "11": "MOTOR3", "12": "MOTOR2", "13": "MOTOR1", "14": "GND"},
    "U2": {"1": "MOTOR1", "2": "MOTOR2", "3": "MOTOR3", "4": "MOTOR4", "8": "GND", "9": "+5V", "13": "COIL_D", "14": "COIL_C", "15": "COIL_B", "16": "COIL_A"},
}


def check(board_path: Path) -> None:
    board = pcbnew.LoadBoard(str(board_path))
    footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}

    for reference, expected in EXPECTED_PINS.items():
        if reference not in footprints:
            raise AssertionError(f"missing footprint {reference}")
        actual = {pad.GetNumber(): pad.GetNetname() for pad in footprints[reference].Pads()}
        for number, net in expected.items():
            if actual.get(number) != net:
                raise AssertionError(f"{reference}.{number}: expected {net}, got {actual.get(number)}")

    outline = board.GetBoardEdgesBoundingBox()
    width = pcbnew.ToMM(outline.GetWidth())
    height = pcbnew.ToMM(outline.GetHeight())
    if abs(width - 35.0) > 0.1 or abs(height - 70.0) > 0.1:
        raise AssertionError(f"unexpected board size {width:.3f} x {height:.3f} mm")

    mounting_holes = [footprints.get(f"H{index}") for index in range(1, 5)]
    if any(hole is None or not hole.IsBoardOnly() for hole in mounting_holes):
        raise AssertionError("four board-only M3 mounting holes are required")

    if board.GetConnectivity().GetUnconnectedCount(False) != 0:
        raise AssertionError("PCB connectivity contains unrouted connections")

    nominal_widths = {}
    for item in board.GetTracks():
        if item.Type() == pcbnew.PCB_TRACE_T:
            nominal_widths.setdefault(item.GetNetname(), set()).add(round(pcbnew.ToMM(item.GetWidth()), 3))

    for net in ("+5V", "GND"):
        if 1.0 not in nominal_widths.get(net, set()):
            raise AssertionError(f"{net} has no 1.0 mm power routing")
    for net in ("COIL_A", "COIL_B", "COIL_C", "COIL_D"):
        if nominal_widths.get(net) != {0.5}:
            raise AssertionError(f"{net} is not routed at 0.5 mm")

    print(f"OK: {width:.2f} x {height:.2f} mm, {len(footprints)} footprints, 0 unrouted connections")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, required=True)
    args = parser.parse_args()
    check(args.board)


if __name__ == "__main__":
    main()
