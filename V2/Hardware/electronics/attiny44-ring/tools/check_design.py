#!/usr/bin/env python3
"""Check the electrical and mechanical invariants of the V2 module PCB."""

from __future__ import annotations

import argparse
from pathlib import Path

import pcbnew


EXPECTED_PINS = {
    "J1": {"1": "LATCH_CONN", "2": "CLOCK_TOP", "3": "DATA_CHAIN_IN", "4": "+5V_CHAIN", "5": "DATA_OUT_CHAIN", "6": "GND"},
    "J3": {"1": "MOTOR1", "2": "MOTOR2", "3": "MOTOR3", "4": "MOTOR4"},
    "J5": {"1": "DATA_OUT_A", "2": "ISP_VCC", "3": "CLOCK_U1", "4": "DATA_IN", "5": "RESET", "6": "GND"},
    "U1": {"1": "+5V_U1", "4": "RESET", "6": "LATCH_A", "7": "DATA_IN", "8": "DATA_OUT_A", "9": "CLOCK_U1", "10": "MOTOR4", "11": "MOTOR3", "12": "MOTOR2", "13": "MOTOR1", "14": "GND"},
    "JP21": {"1": "+5V_MID", "2": "+5V_TOP"},
    "JP22": {"1": "LATCH_CONN", "2": "LATCH_TOP"},
    "JP23": {"1": "+5V", "2": "+5V_MID"},
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
    if abs(width - 50.0) > 0.1 or abs(height - 57.0) > 0.1:
        raise AssertionError(f"unexpected board size {width:.3f} x {height:.3f} mm")

    if any(reference.startswith("H") for reference in footprints):
        raise AssertionError("compact board must not contain mounting holes")

    if board.GetConnectivity().GetUnconnectedCount(False) != 0:
        raise AssertionError("PCB connectivity contains unrouted connections")

    nominal_widths = {}
    for item in board.GetTracks():
        if item.Type() == pcbnew.PCB_TRACE_T:
            nominal_widths.setdefault(item.GetNetname(), set()).add(round(pcbnew.ToMM(item.GetWidth()), 3))

    if any(item.Type() == pcbnew.PCB_VIA_T for item in board.GetTracks()):
        raise AssertionError("vias are not permitted; use 1206 zero-ohm links")
    if any(item.GetLayer() != pcbnew.F_Cu for item in board.GetTracks() if item.Type() == pcbnew.PCB_TRACE_T):
        raise AssertionError("all copper routing must remain on F.Cu")
    for net, widths in nominal_widths.items():
        if min(widths) < 0.406:
            raise AssertionError(f"{net} contains a track narrower than 16 mil")
    if any(widths != {0.406} for widths in nominal_widths.values()):
        raise AssertionError("every routed net must use the 16 mil milling width")

    smd_2x3 = [
        reference for reference, footprint in footprints.items()
        if footprint.GetFPID().GetLibItemName().wx_str() == "PinHeader_2x03_P2.54mm_Vertical_SMD"
    ]
    if sorted(smd_2x3) != ["J1", "J5"]:
        raise AssertionError(f"expected only J1 and J5 as SMD 2x3 headers, got {sorted(smd_2x3)}")

    passives = [reference for reference in footprints if reference.startswith(("R", "C", "JP"))]
    for reference in passives:
        if "1206_3216Metric" not in footprints[reference].GetFPID().GetLibItemName().wx_str():
            raise AssertionError(f"{reference} does not use a 1206 footprint")

    print(f"OK: {width:.2f} x {height:.2f} mm, {len(footprints)} footprints, 0 unrouted connections")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, required=True)
    args = parser.parse_args()
    check(args.board)


if __name__ == "__main__":
    main()
