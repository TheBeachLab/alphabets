#!/usr/bin/env python3
"""Generate the placed, single-sided Alphabets V2 ATtiny1624 PCB."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pcbnew


MM = pcbnew.FromMM
BOARD_LEFT = 99.0
BOARD_TOP = 100.0
BOARD_RIGHT = 149.0
BOARD_BOTTOM = 150.0
SIGNAL_WIDTH = 0.4064  # 16 mil
POWER_WIDTH = SIGNAL_WIDTH
ISOLATION = 0.4


NETS = [
    "+5V_MAIN",
    "+5V_MAIN_TOP",
    "+5V_MCU_SOURCE",
    "+5V_CHAIN",
    "+5V_HOME",
    "+5V_UPDI",
    "+5V_U1",
    "GND",
    "GND_CHAIN",
    "GND_U1",
    "CLOCK_CONN",
    "CLOCK_U1",
    "LATCH_CONN",
    "LATCH_U1",
    "DATA_CHAIN_IN",
    "DATA_IN_U1",
    "DATA_OUT_U1",
    "DATA_OUT_CHAIN",
    "UPDI_PROG",
    "UPDI_U1",
    "HOME",
    "MOTOR1_U1",
    "MOTOR1_DRIVER",
    "MOTOR2_U1",
    "MOTOR2_DRIVER",
    "MOTOR3_U1",
    "MOTOR3_DRIVER",
    "MOTOR4",
    "unconnected-(J5-NC-Pad3)",
    "unconnected-(J5-NC-Pad4)",
    "unconnected-(J5-NC-Pad5)",
    "unconnected-(U1-PA6-Pad4)",
    "unconnected-(U1-PA7-Pad5)",
]


DATASHEETS = {
    "U1": "https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny1624-26-27-DataSheet-DS40002234B.pdf",
}


PARTS = [
    ("J1", "Connector_PinHeader_2.54mm", "PinHeader_2x03_P2.54mm_Vertical_SMD", "CHAIN_RING", (105.4, 108.12), 0, {"1": "LATCH_CONN", "2": "CLOCK_CONN", "3": "DATA_CHAIN_IN", "4": "+5V_CHAIN", "5": "DATA_OUT_CHAIN", "6": "GND_CHAIN"}),
    ("J3", "Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical_SMD_Pin1Left", "STEPPER_DRIVER_IN", (104.0, 141.5), 0, {"1": "MOTOR1_DRIVER", "2": "MOTOR2_DRIVER", "3": "MOTOR3_DRIVER", "4": "MOTOR4"}),
    ("J4", "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical_SMD_Pin1Left", "HOME_SENSOR", (123.0, 141.5), 0, {"1": "+5V_HOME", "2": "HOME", "3": "GND"}),
    ("J5", "Connector_PinHeader_2.54mm", "PinHeader_2x03_P2.54mm_Vertical_SMD", "UPDI_2X3", (141.8, 108.12), 0, {"1": "UPDI_PROG", "2": "+5V_UPDI", "3": "unconnected-(J5-NC-Pad3)", "4": "unconnected-(J5-NC-Pad4)", "5": "unconnected-(J5-NC-Pad5)", "6": "GND"}),
    ("U1", "Package_SO", "SOIC-14_3.9x8.7mm_P1.27mm", "ATtiny1624-SSU", (124.0, 126.0), 0, {"1": "+5V_U1", "2": "LATCH_U1", "3": "HOME", "4": "unconnected-(U1-PA6-Pad4)", "5": "unconnected-(U1-PA7-Pad5)", "6": "MOTOR4", "7": "MOTOR3_U1", "8": "MOTOR2_U1", "9": "MOTOR1_U1", "10": "UPDI_U1", "11": "DATA_IN_U1", "12": "DATA_OUT_U1", "13": "CLOCK_U1", "14": "GND_U1"}),
    ("R1", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "10k UPDI pull-up 1206", (136.0, 116.0), 0, {"1": "+5V_UPDI", "2": "UPDI_PROG"}),
    ("R2", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "10k HOME pull-up 1206", (115.0, 134.0), 0, {"1": "+5V_HOME", "2": "HOME"}),
    ("C1", "Capacitor_SMD", "C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", "100n MCU 1206", (120.0, 117.0), 0, {"1": "+5V_U1", "2": "GND_U1"}),
    ("C2", "Capacitor_SMD", "C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", "1n HF 1206", (125.0, 117.0), 0, {"1": "+5V_U1", "2": "GND_U1"}),
    ("C3", "Capacitor_SMD", "C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", "10u BULK 1206", (144.5, 121.0), 90, {"1": "+5V_UPDI", "2": "GND"}),
    ("JP1", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R CHAIN power bridge 1206", (115.0, 105.0), 0, {"1": "+5V_CHAIN", "2": "+5V_MAIN_TOP"}),
    ("JP2", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R UPDI power bridge 1206", (132.0, 105.0), 0, {"1": "+5V_UPDI", "2": "+5V_MAIN_TOP"}),
    ("JP3", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R HOME power bridge 1206", (123.0, 135.0), 0, {"1": "+5V_HOME", "2": "+5V_MAIN"}),
    ("JP4", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R MCU power bridge 1206", (116.0, 120.0), 90, {"1": "+5V_MCU_SOURCE", "2": "+5V_U1"}),
    ("JP5", "Alphabets", "WireLink_22.3mm_SMD", "INSULATED CLOCK LINK 22.3mm", (121.25, 117.25), -34, {"1": "CLOCK_CONN", "2": "CLOCK_U1"}),
    ("JP6", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R LATCH bridge 1206", (112.0, 121.0), 90, {"1": "LATCH_CONN", "2": "LATCH_U1"}),
    ("JP7", "Alphabets", "WireLink_25.6mm_SMD", "INSULATED DATA_IN LINK 25.6mm", (120.75, 121.0), -23, {"1": "DATA_CHAIN_IN", "2": "DATA_IN_U1"}),
    ("JP8", "Alphabets", "WireLink_23.5mm_SMD", "INSULATED DATA_OUT LINK 23.5mm", (120.5, 119.5), 177.6, {"1": "DATA_OUT_U1", "2": "DATA_OUT_CHAIN"}),
    ("JP9", "Resistor_SMD", "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "0R MCU ground bridge 1206", (132.0, 136.0), 0, {"1": "GND_U1", "2": "GND"}),
    ("JP10", "Alphabets", "WireLink_16.6mm_SMD", "INSULATED UPDI LINK 16.6mm", (134.75, 120.15), -121, {"1": "UPDI_PROG", "2": "UPDI_U1"}),
    ("JP11", "Alphabets", "WireLink_29.7mm_SMD", "INSULATED GND LINK 29.7mm", (115.0, 127.0), -70.3, {"1": "GND_CHAIN", "2": "GND"}),
    ("JP12", "Alphabets", "WireLink_23.5mm_SMD", "INSULATED MOTOR3 LINK 23.5mm", (109.65, 135.035), -139, {"1": "MOTOR3_U1", "2": "MOTOR3_DRIVER"}),
    ("JP13", "Alphabets", "WireLink_17.7mm_SMD", "INSULATED MCU POWER LINK 17.7mm", (120.5, 131.0), 137.3, {"1": "+5V_MAIN", "2": "+5V_MCU_SOURCE"}),
    ("JP14", "Alphabets", "WireLink_30.3mm_SMD", "INSULATED MOTOR1 LINK 30.3mm", (115.25, 134.345), -167.2, {"1": "MOTOR1_U1", "2": "MOTOR1_DRIVER"}),
    ("JP15", "Alphabets", "WireLink_24.5mm_SMD", "INSULATED MOTOR2 LINK 24.5mm", (119.5, 137.75), -159.7, {"1": "MOTOR2_U1", "2": "MOTOR2_DRIVER"}),
    ("JP16", "Alphabets", "WireLink_27.0mm_SMD", "INSULATED MAIN POWER LINK 27.0mm", (124.5, 118.5), -90, {"1": "+5V_MAIN_TOP", "2": "+5V_MAIN"}),
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


def add_route(board: pcbnew.BOARD, net, points) -> None:
    for start, end in zip(points, points[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vec(*start))
        track.SetEnd(vec(*end))
        track.SetLayer(pcbnew.F_Cu)
        track.SetWidth(MM(SIGNAL_WIDTH))
        track.SetNet(net)
        track.SetLocked(True)
        board.Add(track)


def pad_position(board: pcbnew.BOARD, reference: str, number: str) -> tuple[float, float]:
    footprint = board.FindFootprintByReference(reference)
    pad = next(pad for pad in footprint.Pads() if pad.GetNumber() == number)
    position = pad.GetPosition()
    return (pcbnew.ToMM(position.x), pcbnew.ToMM(position.y))


def load_footprint(root: Path, library: str, name: str):
    if library == "Alphabets":
        footprint_dir = Path(__file__).resolve().parent.parent / "Alphabets.pretty"
    else:
        footprint_dir = root / f"{library}.pretty"
    footprint = pcbnew.FootprintLoad(str(footprint_dir), name)
    if footprint is None:
        raise RuntimeError(f"Cannot load {library}:{name}")
    return footprint


def generate(output: Path, dsn_output: Path, footprint_root: Path) -> None:
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    board.GetTitleBlock().SetTitle("Alphabets V2 ATtiny1624 millable ring module")
    board.GetTitleBlock().SetRevision("1.0")
    board.GetTitleBlock().SetCompany("TheBeachLab / Alphabets")
    board.GetTitleBlock().SetComment(0, "Single-sided F.Cu; 16-20 mil organic tracks; 0.4 mm isolation")

    default_class = board.GetAllNetClasses()["Default"]
    default_class.SetClearance(MM(ISOLATION))
    default_class.SetTrackWidth(MM(SIGNAL_WIDTH))

    net_settings = board.GetDesignSettings().m_NetSettings
    power_class = pcbnew.NETCLASS("Power")
    power_class.SetClearance(MM(ISOLATION))
    power_class.SetTrackWidth(MM(POWER_WIDTH))
    net_settings.SetNetclass("Power", power_class)
    for pattern in ("+5V*", "GND*"):
        net_settings.SetNetclassPatternAssignment(pattern, "Power")

    net_objects = {}
    for name in NETS:
        net = pcbnew.NETINFO_ITEM(board, name)
        if name.startswith("+5V") or name.startswith("GND"):
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

    add_text(board, "A2 / ATtiny1624", (124.0, 102.0), size=0.9)
    add_text(board, "CHAIN", (105.4, 113.4))
    add_text(board, "UPDI", (141.8, 113.4))
    add_text(board, "DRIVER", (110.0, 147.5))
    add_text(board, "HOME", (123.0, 147.5))

    add_route(
        board,
        net_objects["+5V_UPDI"],
        [
            pad_position(board, "JP2", "1"),
            (130.45, 101.0),
            (147.5, 101.0),
            (147.5, 105.58),
            pad_position(board, "J5", "2"),
            (147.8, 105.58),
            (147.8, 122.5625),
            pad_position(board, "C3", "1"),
        ],
    )
    add_route(
        board,
        net_objects["CLOCK_CONN"],
        [
            pad_position(board, "J1", "2"),
            (110.0, 103.5),
            (112.006, 103.5),
            pad_position(board, "JP5", "1"),
        ],
    )

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
