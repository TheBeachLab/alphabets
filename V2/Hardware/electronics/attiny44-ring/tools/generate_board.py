#!/usr/bin/env python3
"""Generate the placed, single-sided Alphabets V2 ATtiny44 PCB."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pcbnew


MM = pcbnew.FromMM
BOARD_LEFT = 100.0
BOARD_TOP = 100.0
BOARD_RIGHT = 149.0
BOARD_BOTTOM = 157.0
SIGNAL_WIDTH = 0.4064  # 16 mil
POWER_WIDTH = SIGNAL_WIDTH
ISOLATION = 0.4


NETS = [
    "+5V",
    "+5V_CHAIN",
    "+5V_MID",
    "+5V_TOP",
    "+5V_U1",
    "GND",
    "CLOCK_A",
    "CLOCK_U1",
    "CLOCK_TOP",
    "LATCH_A",
    "LATCH_CONN",
    "LATCH_TOP",
    "DATA_TOP",
    "DATA_CHAIN_IN",
    "DATA_IN",
    "DATA_OUT_A",
    "DATA_OUT_CHAIN",
    "RESET",
    "ISP_VCC",
    "MOTOR1",
    "MOTOR2",
    "MOTOR3",
    "MOTOR4",
    "unconnected-(U1-PB0-Pad2)",
    "unconnected-(U1-PB1-Pad3)",
    "unconnected-(U1-HOME{slash}PB2-Pad5)",
]


DATASHEETS = {
    "U1": "https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny24A-44A-84A-DataSheet-DS40002269A.pdf",
}


PARTS = [
    ("J1", "Connector_PinHeader_2.54mm", "PinHeader_2x03_P2.54mm_Vertical_SMD", "CHAIN_RING", (105.4, 108.12), 0, {"1": "LATCH_TOP", "2": "CLOCK_TOP", "3": "DATA_CHAIN_IN", "4": "+5V_CHAIN", "5": "DATA_OUT_CHAIN", "6": "GND"}),
    ("J3", "Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical_SMD_Pin1Left", "STEPPER_DRIVER_IN", (135.8, 131.52), 0, {"1": "MOTOR1", "2": "MOTOR2", "3": "MOTOR3", "4": "MOTOR4"}),
    ("J5", "Connector_PinHeader_2.54mm", "PinHeader_2x03_P2.54mm_Vertical_SMD", "AVR_ISP_2X3", (131.8, 151.02), 0, {"1": "DATA_OUT_A", "2": "ISP_VCC", "3": "CLOCK_U1", "4": "DATA_IN", "5": "RESET", "6": "GND"}),
    ("U1", "Package_SO", "SOIC-14_3.9x8.7mm_P1.27mm", "ATtiny44A-SS", (119.8, 129.96), 0, {"1": "+5V_U1", "2": "unconnected-(U1-PB0-Pad2)", "3": "unconnected-(U1-PB1-Pad3)", "4": "RESET", "5": "unconnected-(U1-HOME{slash}PB2-Pad5)", "6": "LATCH_A", "7": "DATA_IN", "8": "DATA_OUT_A", "9": "CLOCK_U1", "10": "MOTOR4", "11": "MOTOR3", "12": "MOTOR2", "13": "MOTOR1", "14": "GND"}),
    ("R2", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "10k RESET pull-up 1206", (109.0, 128.4), 0, {"1": "+5V", "2": "RESET"}),
    ("C1", "Capacitor_SMD", "C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", "100n MCU 1206", (119.8, 123.72), 0, {"1": "+5V_U1", "2": "GND"}),
    ("C2", "Capacitor_SMD", "C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", "10u BULK 1206", (143.8, 115.92), 0, {"1": "+5V", "2": "GND"}),
    ("JP5", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R CLOCK input jumper 1206", (126.8, 124.5), 270, {"1": "CLOCK_TOP", "2": "CLOCK_A"}),
    ("JP6", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R LATCH input jumper 1206", (114.0, 126.8), 270, {"1": "LATCH_TOP", "2": "LATCH_A"}),
    ("JP7", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R DATA input jumper 1206", (113.4, 133.86), 270, {"1": "DATA_IN", "2": "DATA_TOP"}),
    ("JP8", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R CHAIN DATA_OUT jumper 1206", (111.8, 115.14), 90, {"1": "DATA_OUT_A", "2": "DATA_OUT_CHAIN"}),
    ("JP16", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R CLOCK MCU bridge 1206", (126.8, 132.0), 270, {"1": "CLOCK_A", "2": "CLOCK_U1"}),
    ("JP17", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R DATA chain bridge 1206", (105.0, 128.4), 270, {"1": "DATA_CHAIN_IN", "2": "DATA_TOP"}),
    ("JP18", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R MCU power bridge 1206", (115.8, 121.38), 270, {"1": "+5V", "2": "+5V_U1"}),
    ("JP19", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R CHAIN power bridge 1206", (115.0, 104.5), 0, {"1": "+5V_CHAIN", "2": "+5V"}),
    ("JP20", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R ISP VCC bridge 1206", (143.8, 139.32), 90, {"1": "ISP_VCC", "2": "+5V"}),
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


def add_text(board: pcbnew.BOARD, text: str, position, layer=pcbnew.F_SilkS, size=0.8) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(vec(*position))
    item.SetLayer(layer)
    item.SetTextSize(vec(size, size))
    item.SetTextThickness(MM(0.15))
    board.Add(item)


def load_footprint(root: Path, library: str, name: str):
    footprint = pcbnew.FootprintLoad(str(root / f"{library}.pretty"), name)
    if footprint is None:
        raise RuntimeError(f"Cannot load {library}:{name}")
    return footprint


def generate(output: Path, dsn_output: Path, footprint_root: Path) -> None:
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    board.GetTitleBlock().SetTitle("Alphabets V2 ATtiny44 millable ring module")
    board.GetTitleBlock().SetRevision("2.0")
    board.GetTitleBlock().SetCompany("TheBeachLab / Alphabets")
    board.GetTitleBlock().SetComment(0, "Single-sided F.Cu; 16 mil tracks; 0.4 mm isolation")

    default_class = board.GetAllNetClasses()["Default"]
    default_class.SetClearance(MM(ISOLATION))
    default_class.SetTrackWidth(MM(SIGNAL_WIDTH))

    net_settings = board.GetDesignSettings().m_NetSettings
    power_class = pcbnew.NETCLASS("Power")
    power_class.SetClearance(MM(ISOLATION))
    power_class.SetTrackWidth(MM(POWER_WIDTH))
    net_settings.SetNetclass("Power", power_class)
    net_settings.SetNetclassPatternAssignment("+5V", "Power")
    net_settings.SetNetclassPatternAssignment("+5V_U1", "Power")
    net_settings.SetNetclassPatternAssignment("GND", "Power")

    net_objects = {}
    for name in NETS:
        net = pcbnew.NETINFO_ITEM(board, name)
        if name in ("+5V", "+5V_TOP", "+5V_U1", "GND"):
            net.SetNetClass(power_class)
        board.Add(net)
        net_objects[name] = net

    for reference, library, footprint_name, value, position, angle, pad_nets in PARTS:
        footprint = load_footprint(footprint_root, library, footprint_name)
        footprint.SetReference(reference)
        footprint.SetValue(value)
        footprint.SetFPIDAsString(f"{library}:{footprint_name}")
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

    add_segment(board, (BOARD_LEFT, BOARD_TOP), (BOARD_RIGHT, BOARD_TOP), pcbnew.Edge_Cuts)
    add_segment(board, (BOARD_RIGHT, BOARD_TOP), (BOARD_RIGHT, BOARD_BOTTOM), pcbnew.Edge_Cuts)
    add_segment(board, (BOARD_LEFT, BOARD_BOTTOM), (BOARD_LEFT, BOARD_TOP), pcbnew.Edge_Cuts)
    add_segment(board, (BOARD_RIGHT, BOARD_BOTTOM), (BOARD_LEFT, BOARD_BOTTOM), pcbnew.Edge_Cuts)

    add_text(board, "ALPHABETS V2", (132.0, 102.0), size=0.9)

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
    parser.add_argument("--footprints", type=Path, default=Path(os.environ["KICAD10_FOOTPRINT_DIR"]))
    args = parser.parse_args()
    generate(args.output, args.dsn, args.footprints)


if __name__ == "__main__":
    main()
