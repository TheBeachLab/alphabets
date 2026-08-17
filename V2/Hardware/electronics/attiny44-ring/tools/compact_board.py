#!/usr/bin/env python3
"""Compact the routed PCB around its useful copper and components."""

from __future__ import annotations

import argparse
from pathlib import Path

import pcbnew


MM = pcbnew.FromMM
BOARD_LEFT = 99.0
BOARD_TOP = 100.0
BOARD_RIGHT = 149.0
BOARD_BOTTOM = 157.0
FABRICATION_WIDTH = 0.4064  # 16 mil
ISOLATION = 0.4

DATA_CHAIN_ROUTE = [
    (102.875, 108.12),
    (100.67, 108.12),
    (99.811, 108.979),
    (99.811, 125.66),
    (101.0, 126.85),
    (105.0, 126.85),
]

LATCH_CONNECTOR_ROUTE = [
    (102.875, 105.58),
    (105.08, 105.58),
    (105.08, 108.886),
    (104.576, 109.39),
    (101.162, 109.39),
    (100.67, 109.883),
    (100.67, 113.84),
]


def vec(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(MM(x), MM(y))


def add_segment(board: pcbnew.BOARD, start, end) -> None:
    line = pcbnew.PCB_SHAPE(board)
    line.SetShape(pcbnew.SHAPE_T_SEGMENT)
    line.SetStart(vec(*start))
    line.SetEnd(vec(*end))
    line.SetLayer(pcbnew.Edge_Cuts)
    line.SetWidth(MM(0.05))
    board.Add(line)


def add_text(board: pcbnew.BOARD, text: str, position, size: float = 0.8) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(vec(*position))
    item.SetLayer(pcbnew.F_SilkS)
    item.SetTextSize(vec(size, size))
    item.SetTextThickness(MM(0.15))
    board.Add(item)


def add_route(board: pcbnew.BOARD, net_name: str, points) -> None:
    net = board.FindNet(net_name)
    if net is None:
        raise AssertionError(f"missing net {net_name}")
    for start, end in zip(points, points[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vec(*start))
        track.SetEnd(vec(*end))
        track.SetLayer(pcbnew.F_Cu)
        track.SetWidth(MM(FABRICATION_WIDTH))
        track.SetNet(net)
        board.Add(track)


def load_link(
    board: pcbnew.BOARD,
    reference: str,
    value: str,
    position,
    angle: float,
):
    local_library = Path(__file__).resolve().parent.parent / "Alphabets.pretty"
    footprint = pcbnew.FootprintLoad(
        str(local_library),
        "R_1206_3216Metric_CompactCrossover",
    )
    if footprint is None:
        raise RuntimeError("cannot load compact 1206 zero-ohm footprint")
    footprint.SetReference(reference)
    footprint.SetValue(value)
    footprint.SetFPIDAsString("Alphabets:R_1206_3216Metric_CompactCrossover")
    footprint.SetPosition(vec(*position))
    footprint.SetOrientationDegrees(angle)
    footprint.Reference().SetVisible(False)
    footprint.Value().SetVisible(False)
    board.Add(footprint)
    return footprint


def pad_position(footprint, number: str) -> tuple[float, float]:
    pad = next(pad for pad in footprint.Pads() if pad.GetNumber() == number)
    position = pad.GetPosition()
    return (pcbnew.ToMM(position.x), pcbnew.ToMM(position.y))


def get_or_create_net(board: pcbnew.BOARD, name: str):
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def compact(board_path: Path) -> None:
    board = pcbnew.LoadBoard(str(board_path))
    footprints = list(board.GetFootprints())
    tracks = list(board.GetTracks())
    drawings = list(board.GetDrawings())
    netclasses = list(board.GetAllNetClasses().values())

    for netclass in netclasses:
        netclass.SetClearance(MM(ISOLATION))
        netclass.SetTrackWidth(MM(FABRICATION_WIDTH))

    for footprint in footprints:
        if footprint.GetReference().startswith("H"):
            board.Remove(footprint)

    for track in tracks:
        if track.Type() != pcbnew.PCB_TRACE_T:
            raise AssertionError("compact board must not contain vias")
        track.SetWidth(MM(FABRICATION_WIDTH))

    unconnected = board.GetConnectivity().GetUnconnectedCount(False)
    if unconnected == 3:
        nets = {
            name: get_or_create_net(board, name)
            for name in ("+5V", "+5V_MID", "+5V_TOP", "LATCH_CONN", "LATCH_TOP")
        }

        by_reference = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
        pad_assignments = {
            ("J1", "1"): "LATCH_CONN",
            ("C2", "1"): "+5V_TOP",
            ("JP19", "2"): "+5V_TOP",
            ("JP20", "2"): "+5V_TOP",
        }
        for (reference, number), net_name in pad_assignments.items():
            pad = next(pad for pad in by_reference[reference].Pads() if pad.GetNumber() == number)
            pad.SetNet(nets[net_name])

        for track in tracks:
            if track.GetNetname() == "+5V":
                x_max = max(pcbnew.ToMM(track.GetStart().x), pcbnew.ToMM(track.GetEnd().x))
                if x_max > 120.0:
                    track.SetNet(nets["+5V_TOP"])

        jp21 = load_link(
            board,
            "JP21",
            "0R POWER crossover 1 1206",
            (122.5, 118.65),
            45,
        )
        jp22 = load_link(
            board,
            "JP22",
            "0R LATCH crossover 1206",
            (107.45, 122.0),
            0,
        )
        jp23 = load_link(
            board,
            "JP23",
            "0R POWER crossover 2 1206",
            (116.55, 116.06),
            45,
        )
        jp21_pads = {pad.GetNumber(): pad for pad in jp21.Pads()}
        jp22_pads = {pad.GetNumber(): pad for pad in jp22.Pads()}
        jp23_pads = {pad.GetNumber(): pad for pad in jp23.Pads()}
        jp21_pads["1"].SetNet(nets["+5V_MID"])
        jp21_pads["2"].SetNet(nets["+5V_TOP"])
        jp22_pads["1"].SetNet(nets["LATCH_CONN"])
        jp22_pads["2"].SetNet(nets["LATCH_TOP"])
        jp23_pads["1"].SetNet(nets["+5V"])
        jp23_pads["2"].SetNet(nets["+5V_MID"])

        add_route(board, "DATA_CHAIN_IN", DATA_CHAIN_ROUTE)
        add_route(board, "LATCH_CONN", LATCH_CONNECTOR_ROUTE + [pad_position(jp22, "1")])
        add_route(board, "LATCH_TOP", [pad_position(jp22, "2"), (114.0, 125.25)])
        add_route(
            board,
            "+5V_TOP",
            [
                (127.97, 115.92),
                pad_position(jp21, "2"),
            ],
        )
        add_route(board, "+5V_MID", [pad_position(jp21, "1"), pad_position(jp23, "2")])
        add_route(board, "+5V", [pad_position(jp23, "1"), (115.8, 118.4074)])
    elif unconnected != 0:
        raise AssertionError(f"expected three autorouter gaps, got {unconnected}")

    for item in drawings:
        if item.GetLayer() == pcbnew.Edge_Cuts or item.Type() == pcbnew.PCB_TEXT_T:
            board.Remove(item)

    add_segment(board, (BOARD_LEFT, BOARD_TOP), (BOARD_RIGHT, BOARD_TOP))
    add_segment(board, (BOARD_RIGHT, BOARD_TOP), (BOARD_RIGHT, BOARD_BOTTOM))
    add_segment(board, (BOARD_RIGHT, BOARD_BOTTOM), (BOARD_LEFT, BOARD_BOTTOM))
    add_segment(board, (BOARD_LEFT, BOARD_BOTTOM), (BOARD_LEFT, BOARD_TOP))

    add_text(board, "A2 / 16 mil", (133.0, 102.0), 0.9)
    add_text(board, "CHAIN", (105.5, 113.4))
    add_text(board, "DRIVER", (135.8, 138.2))
    add_text(board, "ISP", (131.8, 156.0))

    board.GetTitleBlock().SetComment(0, "Single-sided F.Cu; 16 mil tracks; 0.4 mm isolation")
    if not pcbnew.SaveBoard(str(board_path), board):
        raise RuntimeError(f"Could not save {board_path}")
    verified = pcbnew.LoadBoard(str(board_path))
    remaining = verified.GetConnectivity().GetUnconnectedCount(False)
    if remaining:
        raise AssertionError(f"compact board still has {remaining} unrouted connections")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, required=True)
    args = parser.parse_args()
    compact(args.board)


if __name__ == "__main__":
    main()
