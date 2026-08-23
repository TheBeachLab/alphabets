#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Check the electrical and mechanical invariants of the ATtiny1624 module PCB."""

from __future__ import annotations

import argparse
from pathlib import Path

import pcbnew


EXPECTED_PINS = {
    "J1": {"1": "LATCH_CONN", "2": "CLOCK_CONN", "3": "DATA_CHAIN_IN", "4": "+5V_CHAIN", "5": "DATA_OUT_CHAIN", "6": "GND_CHAIN"},
    "J3": {"1": "MOTOR1_DRIVER", "2": "MOTOR2_DRIVER", "3": "MOTOR3_DRIVER", "4": "MOTOR4"},
    "J4": {"1": "+5V_HOME", "2": "HOME", "3": "GND"},
    "J5": {"1": "UPDI_PROG", "2": "+5V_UPDI", "3": "unconnected-(J5-NC-Pad3)", "4": "unconnected-(J5-NC-Pad4)", "5": "unconnected-(J5-NC-Pad5)", "6": "GND"},
    "U1": {"1": "+5V_U1", "2": "LATCH_U1", "3": "HOME", "4": "unconnected-(U1-PA6-Pad4)", "5": "unconnected-(U1-PA7-Pad5)", "6": "MOTOR4", "7": "MOTOR3_U1", "8": "MOTOR2_U1", "9": "MOTOR1_U1", "10": "UPDI_U1", "11": "DATA_IN_U1", "12": "DATA_OUT_U1", "13": "CLOCK_U1", "14": "GND_U1"},
    "JP1": {"1": "+5V_CHAIN", "2": "+5V_MAIN_TOP"},
    "JP2": {"1": "+5V_UPDI", "2": "+5V_MAIN_TOP"},
    "JP3": {"1": "+5V_HOME", "2": "+5V_MAIN"},
    "JP4": {"1": "+5V_MCU_SOURCE", "2": "+5V_U1"},
    "JP5": {"1": "CLOCK_CONN", "2": "CLOCK_U1"},
    "JP6": {"1": "LATCH_CONN", "2": "LATCH_U1"},
    "JP7": {"1": "DATA_CHAIN_IN", "2": "DATA_IN_U1"},
    "JP8": {"1": "DATA_OUT_U1", "2": "DATA_OUT_CHAIN"},
    "JP9": {"1": "GND_U1", "2": "GND"},
    "JP10": {"1": "UPDI_PROG", "2": "UPDI_U1"},
    "JP11": {"1": "GND_CHAIN", "2": "GND"},
    "JP12": {"1": "MOTOR3_U1", "2": "MOTOR3_DRIVER"},
    "JP13": {"1": "+5V_MAIN", "2": "+5V_MCU_SOURCE"},
    "JP14": {"1": "MOTOR1_U1", "2": "MOTOR1_DRIVER"},
    "JP15": {"1": "MOTOR2_U1", "2": "MOTOR2_DRIVER"},
    "JP16": {"1": "+5V_MAIN_TOP", "2": "+5V_MAIN"},
}


def check(board_path: Path) -> None:
    board = pcbnew.LoadBoard(str(board_path))
    footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}

    for reference, expected in EXPECTED_PINS.items():
        if reference not in footprints:
            raise AssertionError(f"missing footprint {reference}")
        actual = {pad.GetNumber(): pad.GetNetname() for pad in footprints[reference].Pads()}
        for number, net in expected.items():
            if actual.get(number, "") != net:
                raise AssertionError(f"{reference}.{number}: expected {net!r}, got {actual.get(number)!r}")

    if len(footprints) != 26:
        raise AssertionError(f"expected 26 footprints, got {len(footprints)}")

    outline = board.GetBoardEdgesBoundingBox()
    width = pcbnew.ToMM(outline.GetWidth())
    height = pcbnew.ToMM(outline.GetHeight())
    if abs(width - 50.0) > 0.1 or abs(height - 50.0) > 0.1:
        raise AssertionError(f"unexpected board size {width:.3f} x {height:.3f} mm")

    if board.GetConnectivity().GetUnconnectedCount(False) != 0:
        raise AssertionError("PCB connectivity contains unrouted connections")

    copper_items = [
        item for item in board.GetTracks()
        if item.GetClass() in ("PCB_TRACK", "PCB_ARC")
    ]
    if any(item.Type() == pcbnew.PCB_VIA_T for item in board.GetTracks()):
        raise AssertionError("vias are not permitted; use 1206 zero-ohm links")
    if any(item.GetLayer() != pcbnew.F_Cu for item in copper_items):
        raise AssertionError("all copper routing must remain on F.Cu")

    nominal_widths = {
        round(pcbnew.ToMM(item.GetWidth()), 3)
        for item in copper_items
    }
    if nominal_widths and min(nominal_widths) < 0.406:
        raise AssertionError("routed copper contains a track narrower than 16 mil")
    if not nominal_widths.issubset({0.406, 0.508}):
        raise AssertionError(f"unexpected routed widths: {sorted(nominal_widths)}")

    arcs = sum(item.GetClass() == "PCB_ARC" for item in copper_items)
    arc_radii = {
        round(pcbnew.ToMM(item.GetRadius()), 3)
        for item in copper_items if item.GetClass() == "PCB_ARC"
    }
    pad_teardrops = [zone for zone in board.Zones() if zone.GetAssignedPriority() >= 100]
    if arcs < 40:
        raise AssertionError(f"expected organic routing arcs, found only {arcs}")
    if len(arc_radii) < 8:
        raise AssertionError("organic routing lacks variable-radius corners")
    if len(pad_teardrops) < 25:
        raise AssertionError(f"expected pad teardrops, found only {len(pad_teardrops)}")

    smd_2x3 = [
        reference for reference, footprint in footprints.items()
        if footprint.GetFPID().GetLibItemName().wx_str() == "PinHeader_2x03_P2.54mm_Vertical_SMD"
    ]
    if sorted(smd_2x3) != ["J1", "J5"]:
        raise AssertionError(f"expected J1 and J5 as SMD 2x3 headers, got {sorted(smd_2x3)}")

    passives = [reference for reference in footprints if reference.startswith(("R", "C", "JP"))]
    for reference in passives:
        footprint_name = footprints[reference].GetFPID().GetLibItemName().wx_str()
        if reference in ("JP5", "JP7", "JP8", "JP10", "JP11", "JP12", "JP13", "JP14", "JP15", "JP16"):
            if not footprint_name.startswith("WireLink_"):
                raise AssertionError(f"{reference} does not use an insulated SMD wire-link footprint")
        elif "1206_3216Metric" not in footprint_name:
            raise AssertionError(f"{reference} does not use a 1206 footprint")

    total_length = sum(item.GetLength() for item in copper_items)
    wide_length = sum(
        item.GetLength() for item in copper_items
        if round(pcbnew.ToMM(item.GetWidth()), 3) == 0.508
    )
    wide_ratio = wide_length / total_length if total_length else 0
    print(
        f"OK: {width:.2f} x {height:.2f} mm, {len(footprints)} footprints, "
        f"{wide_ratio:.1%} at 20 mil, {arcs} variable-radius arcs, "
        f"{len(pad_teardrops)} pad teardrops, 0 unrouted connections"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, required=True)
    args = parser.parse_args()
    check(args.board)


if __name__ == "__main__":
    main()
