#!/usr/bin/env python3
"""Generate the placed Alphabets V2 ATtiny44 ring PCB and Specctra DSN."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pcbnew


MM = pcbnew.FromMM
BOARD_LEFT = 100.0
BOARD_TOP = 100.0
BOARD_RIGHT = 135.0
BOARD_BOTTOM = 170.0


NETS = [
    "+5V",
    "GND",
    "CLOCK",
    "LATCH",
    "DATA_IN",
    "DATA_OUT",
    "RETURN",
    "HOME",
    "RESET",
    "PB0",
    "PB1",
    "MOTOR1",
    "MOTOR2",
    "MOTOR3",
    "MOTOR4",
    "COIL_A",
    "COIL_B",
    "COIL_C",
    "COIL_D",
    "unconnected-(U2-5B-Pad5)",
    "unconnected-(U2-6B-Pad6)",
    "unconnected-(U2-7B-Pad7)",
    "unconnected-(U2-7C-Pad10)",
    "unconnected-(U2-6C-Pad11)",
    "unconnected-(U2-5C-Pad12)",
]


DATASHEETS = {
    "U1": "https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny24A-44A-84A-DataSheet-DS40002269A.pdf",
    "U2": "https://www.st.com/resource/en/datasheet/uln2001.pdf",
}


PARTS = [
    ("J1", "Connector_JST", "JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical", "CHAIN_IN", (117.5, 116.5), 90, {"1": "+5V", "2": "GND", "3": "CLOCK", "4": "LATCH", "5": "DATA_IN", "6": "RETURN"}),
    ("J2", "Connector_JST", "JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical", "CHAIN_OUT", (117.5, 154.0), 270, {"1": "+5V", "2": "GND", "3": "CLOCK", "4": "LATCH", "5": "DATA_OUT", "6": "RETURN"}),
    ("J3", "Connector_JST", "JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical", "28BYJ-48", (110.0, 124.5), 0, {"1": "COIL_A", "2": "COIL_B", "3": "COIL_C", "4": "COIL_D", "5": "+5V"}),
    ("J4", "Connector_JST", "JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical", "HOME_SENSOR", (129.0, 154.0), 270, {"1": "+5V", "2": "GND", "3": "HOME"}),
    ("J5", "Connector_IDC", "IDC-Header_2x03_P2.54mm_Vertical", "AVR_ISP_2X3", (106.5, 151.5), 0, {"1": "DATA_OUT", "2": "+5V", "3": "CLOCK", "4": "DATA_IN", "5": "RESET", "6": "GND"}),
    ("J6", "Connector_JST", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical", "5V_INJECT", (129.0, 112.0), 270, {"1": "+5V", "2": "GND"}),
    ("U1", "Package_SO", "SOIC-14_3.9x8.7mm_P1.27mm", "ATtiny44A-SS", (109.0, 133.5), 90, {"1": "+5V", "2": "PB0", "3": "PB1", "4": "RESET", "5": "HOME", "6": "LATCH", "7": "DATA_IN", "8": "DATA_OUT", "9": "CLOCK", "10": "MOTOR4", "11": "MOTOR3", "12": "MOTOR2", "13": "MOTOR1", "14": "GND"}),
    ("U2", "Package_SO", "SOIC-16_3.9x9.9mm_P1.27mm", "ULN2003A", (124.0, 133.5), 90, {"1": "MOTOR1", "2": "MOTOR2", "3": "MOTOR3", "4": "MOTOR4", "5": "unconnected-(U2-5B-Pad5)", "6": "unconnected-(U2-6B-Pad6)", "7": "unconnected-(U2-7B-Pad7)", "8": "GND", "9": "+5V", "10": "unconnected-(U2-7C-Pad10)", "11": "unconnected-(U2-6C-Pad11)", "12": "unconnected-(U2-5C-Pad12)", "13": "COIL_D", "14": "COIL_C", "15": "COIL_B", "16": "COIL_A"}),
    ("R1", "Resistor_SMD", "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", "10k HOME pull-up", (103.5, 143.5), 0, {"1": "+5V", "2": "HOME"}),
    ("R2", "Resistor_SMD", "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", "10k RESET pull-up", (107.5, 143.5), 0, {"1": "+5V", "2": "RESET"}),
    ("C1", "Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder", "100n MCU", (111.5, 143.5), 0, {"1": "+5V", "2": "GND"}),
    ("C2", "Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder", "100n DRIVER", (115.5, 143.5), 0, {"1": "+5V", "2": "GND"}),
    ("C3", "Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder", "10n HOME filter", (119.5, 143.5), 0, {"1": "HOME", "2": "GND"}),
    ("C4", "Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm", "47u 10V", (124.0, 144.5), 0, {"1": "+5V", "2": "GND"}),
    ("TP1", "TestPoint", "TestPoint_Plated_Hole_D2.0mm", "PB0", (132.0, 123.0), 0, {"1": "PB0"}),
    ("TP2", "TestPoint", "TestPoint_Plated_Hole_D2.0mm", "PB1", (132.0, 127.0), 0, {"1": "PB1"}),
]


def vec(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(MM(x), MM(y))


def add_segment(board: pcbnew.BOARD, start, end, layer, width: float = 0.05) -> None:
    line = pcbnew.PCB_SHAPE(board)
    line.SetShape(pcbnew.SHAPE_T_SEGMENT)
    line.SetStart(vec(*start))
    line.SetEnd(vec(*end))
    line.SetLayer(layer)
    line.SetWidth(MM(width))
    board.Add(line)


def add_text(board: pcbnew.BOARD, text: str, position, layer=pcbnew.F_SilkS, size=1.0) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(vec(*position))
    item.SetLayer(layer)
    item.SetTextSize(vec(size, size))
    item.SetTextThickness(MM(0.15))
    if layer == pcbnew.B_SilkS:
        item.SetMirrored(True)
    board.Add(item)


def load_footprint(root: Path, library: str, name: str):
    footprint = pcbnew.FootprintLoad(str(root / f"{library}.pretty"), name)
    if footprint is None:
        raise RuntimeError(f"Cannot load {library}:{name}")
    return footprint


def generate(output: Path, dsn_output: Path, footprint_root: Path) -> None:
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    board.GetTitleBlock().SetTitle("Alphabets V2 ATtiny44 SPI ring module")
    board.GetTitleBlock().SetRevision("1.0")
    board.GetTitleBlock().SetCompany("TheBeachLab / Alphabets")
    board.GetTitleBlock().SetComment(0, "35 x 70 mm, 2 layers, 5 V")

    default_class = board.GetAllNetClasses()["Default"]
    default_class.SetClearance(MM(0.20))
    default_class.SetTrackWidth(MM(0.25))
    default_class.SetViaDiameter(MM(0.70))
    default_class.SetViaDrill(MM(0.35))

    net_settings = board.GetDesignSettings().m_NetSettings
    power_class = pcbnew.NETCLASS("Power")
    power_class.SetClearance(MM(0.25))
    power_class.SetTrackWidth(MM(1.00))
    power_class.SetViaDiameter(MM(1.20))
    power_class.SetViaDrill(MM(0.60))
    net_settings.SetNetclass("Power", power_class)
    net_settings.SetNetclassPatternAssignment("+5V", "Power")
    net_settings.SetNetclassPatternAssignment("GND", "Power")

    coil_class = pcbnew.NETCLASS("MotorCoils")
    coil_class.SetClearance(MM(0.20))
    coil_class.SetTrackWidth(MM(0.50))
    coil_class.SetViaDiameter(MM(0.90))
    coil_class.SetViaDrill(MM(0.45))
    net_settings.SetNetclass("MotorCoils", coil_class)
    for name in ("COIL_A", "COIL_B", "COIL_C", "COIL_D"):
        net_settings.SetNetclassPatternAssignment(name, "MotorCoils")

    net_objects = {}
    for name in NETS:
        net = pcbnew.NETINFO_ITEM(board, name)
        if name in ("+5V", "GND"):
            net.SetNetClass(power_class)
        elif name.startswith("COIL_"):
            net.SetNetClass(coil_class)
        board.Add(net)
        net_objects[name] = net

    for reference, library, footprint_name, value, position, angle, pad_nets in PARTS:
        footprint = load_footprint(footprint_root, library, footprint_name)
        footprint.SetReference(reference)
        footprint.SetValue(value)
        footprint.SetFPIDAsString(f"{library}:{footprint_name}")
        footprint.SetExcludedFromBOM(reference.startswith("TP"))
        if reference in DATASHEETS:
            footprint.SetField("Datasheet", DATASHEETS[reference])
        footprint.SetPosition(vec(*position))
        footprint.SetOrientationDegrees(angle)
        footprint.Reference().SetVisible(False)
        footprint.Value().SetVisible(False)
        board.Add(footprint)
        pads = {pad.GetNumber(): pad for pad in footprint.Pads()}
        for number, net_name in pad_nets.items():
            pads[number].SetNet(net_objects[net_name])

    for index, position in enumerate(((103.0, 103.0), (132.0, 103.0), (103.0, 167.0), (132.0, 167.0)), start=1):
        hole = load_footprint(footprint_root, "MountingHole", "MountingHole_3.2mm_M3")
        hole.SetReference(f"H{index}")
        hole.SetValue("M3")
        hole.SetFPIDAsString("MountingHole:MountingHole_3.2mm_M3")
        hole.SetBoardOnly(True)
        hole.SetExcludedFromBOM(True)
        hole.SetExcludedFromPosFiles(True)
        hole.SetPosition(vec(*position))
        hole.Reference().SetVisible(False)
        hole.Value().SetVisible(False)
        board.Add(hole)

    add_segment(board, (BOARD_LEFT, BOARD_TOP), (BOARD_RIGHT, BOARD_TOP), pcbnew.Edge_Cuts)
    add_segment(board, (BOARD_RIGHT, BOARD_TOP), (BOARD_RIGHT, BOARD_BOTTOM), pcbnew.Edge_Cuts)
    add_segment(board, (BOARD_RIGHT, BOARD_BOTTOM), (BOARD_LEFT, BOARD_BOTTOM), pcbnew.Edge_Cuts)
    add_segment(board, (BOARD_LEFT, BOARD_BOTTOM), (BOARD_LEFT, BOARD_TOP), pcbnew.Edge_Cuts)

    add_text(board, "ALPHABETS V2 / ATtiny44 SPI RING", (117.5, 130.0), layer=pcbnew.B_SilkS, size=0.8)
    add_text(board, "J1 RING IN", (104.5, 111.0), layer=pcbnew.F_Fab, size=0.8)
    add_text(board, "J2 RING OUT", (105.0, 162.0), layer=pcbnew.F_Fab, size=0.8)
    add_text(board, "J3 MOTOR A B C D +5", (117.0, 128.0), layer=pcbnew.F_Fab, size=0.8)
    add_text(board, "U1 ATtiny44", (109.0, 128.5), layer=pcbnew.F_Fab, size=0.8)
    add_text(board, "U2 ULN2003", (124.0, 128.5), layer=pcbnew.F_Fab, size=0.8)
    add_text(board, "J4 HOME", (129.0, 161.5), layer=pcbnew.F_Fab, size=0.8)
    add_text(board, "J5 ISP", (106.5, 145.0), layer=pcbnew.F_Fab, size=0.8)
    add_text(board, "J6 5V", (129.0, 107.0), layer=pcbnew.F_Fab, size=0.8)
    add_text(board, "R1 R2 C1 C2 C3 C4", (113.0, 141.0), layer=pcbnew.F_Fab, size=0.8)
    add_text(board, "RING: 1 +5V  2 GND  3 CLOCK", (117.5, 134.5), layer=pcbnew.B_SilkS, size=0.8)
    add_text(board, "4 LATCH  5 DATA  6 RETURN", (117.5, 136.5), layer=pcbnew.B_SilkS, size=0.8)

    board.BuildListOfNets()
    output.parent.mkdir(parents=True, exist_ok=True)
    dsn_output.parent.mkdir(parents=True, exist_ok=True)
    if not pcbnew.SaveBoard(str(output), board):
        raise RuntimeError(f"Could not save {output}")
    if not pcbnew.ExportSpecctraDSN(board, str(dsn_output)):
        raise RuntimeError(f"Could not export {dsn_output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dsn", type=Path, required=True)
    parser.add_argument(
        "--footprints",
        type=Path,
        default=Path(os.environ["KICAD10_FOOTPRINT_DIR"]),
    )
    args = parser.parse_args()
    generate(args.output, args.dsn, args.footprints)


if __name__ == "__main__":
    main()
