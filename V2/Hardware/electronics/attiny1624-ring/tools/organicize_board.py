#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Create the adaptive-radius, tapered fabrication PCB from routed copper."""

from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew


THIRD_PARTY = Path(__file__).resolve().parent.parent / "third_party"
sys.path.insert(0, str(THIRD_PARTY))

from kicad_round_tracks.round_tracks_action import RoundTracks  # noqa: E402
from kicad_teardrops.td import SetTeardrops  # noqa: E402


MIN_WIDTH_MM = 0.4064  # 16 mil neckdowns
PREFERRED_WIDTH_MM = 0.508  # 20 mil wherever 0.40 mm isolation remains
ROUND_RADIUS_LEVELS_MM = (2.0, 1.2, 0.8, 0.5, 0.3, 0.2)
TAPER_LENGTH_MM = 0.90
IGNORED_DRC_CATEGORIES = {"lib_footprint_issues", "unconnected_items"}
TRACK_REPORT = re.compile(
    r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): Track(?: \(arc\))? \[([^]]+)\]"
)
ARC_REPORT = re.compile(
    r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): Track \(arc\) \[([^]]+)\]"
)


class _Progress:
    def Pulse(self, *_args) -> bool:  # noqa: N802 - KiCad/wx naming
        return True


class _RoundRunner:
    def __init__(self, board: pcbnew.BOARD) -> None:
        self.board = board
        self.prog = _Progress()
        self.created_arcs = []


def _copper_items(board: pcbnew.BOARD):
    return [item for item in board.GetTracks() if item.GetClass() in ("PCB_TRACK", "PCB_ARC")]


def _drc_categories(kicad_cli: Path, board_path: Path, report_path: Path) -> list[str]:
    subprocess.run(
        [str(kicad_cli), "pcb", "drc", "--output", str(report_path), str(board_path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    report = report_path.read_text(encoding="utf-8")
    return [
        match.group(1)
        for match in re.finditer(r"^\[([^]]+)\]:", report, re.MULTILINE)
        if match.group(1) not in IGNORED_DRC_CATEGORIES
    ]


def _item_sort_key(item) -> tuple:
    position = item.GetPosition()
    return (
        -item.GetLength(),
        item.GetNetname(),
        item.GetClass(),
        position.x,
        position.y,
    )


def _nearest_wide_item(items, net: str, x_mm: float, y_mm: float, wide: int):
    candidates = [item for item in items if item.GetWidth() == wide and item.GetNetname() == net]
    if not candidates:
        return None

    def distance(item) -> float:
        position = item.GetPosition()
        return (
            (pcbnew.ToMM(position.x) - x_mm) ** 2
            + (pcbnew.ToMM(position.y) - y_mm) ** 2
        )

    return min(candidates, key=distance)


def _fit_wide_tracks(board: pcbnew.BOARD, kicad_cli: Path, workspace: Path) -> None:
    items = _copper_items(board)
    narrow = pcbnew.FromMM(MIN_WIDTH_MM)
    wide = pcbnew.FromMM(PREFERRED_WIDTH_MM)
    candidate_board = workspace / "candidate.kicad_pcb"
    report_path = workspace / "candidate-drc.rpt"

    for item in items:
        item.SetWidth(wide)

    for iteration in range(12):
        pcbnew.SaveBoard(str(candidate_board), board)
        categories = _drc_categories(kicad_cli, candidate_board, report_path)
        if not categories:
            break

        report = report_path.read_text(encoding="utf-8")
        offenders = []
        for x, y, net in TRACK_REPORT.findall(report):
            item = _nearest_wide_item(items, net, float(x), float(y), wide)
            if item is not None:
                offenders.append(item)

        unique = {id(item): item for item in offenders}
        if not unique:
            raise RuntimeError(
                f"cannot resolve DRC categories after widening: {sorted(set(categories))}"
            )
        for item in unique.values():
            item.SetWidth(narrow)
    else:
        raise RuntimeError("wide-track clearance fitting did not converge")

    # The first pass deliberately removes both sides of track-to-track conflicts.
    # Re-add safe candidates, longest first, to retain as much 20 mil copper as possible.
    candidates = sorted(
        (item for item in items if item.GetWidth() == narrow),
        key=_item_sort_key,
    )
    accepted = 0
    for index, item in enumerate(candidates, start=1):
        item.SetWidth(wide)
        pcbnew.SaveBoard(str(candidate_board), board)
        if _drc_categories(kicad_cli, candidate_board, report_path):
            item.SetWidth(narrow)
        else:
            accepted += 1
        if index % 20 == 0:
            print(f"tested {index}/{len(candidates)} neckdowns; recovered {accepted}")


def _rounded_board(source: Path, radius_indexes: dict) -> tuple[pcbnew.BOARD, list]:
    board = pcbnew.LoadBoard(str(source))
    if any(item.GetClass() == "PCB_ARC" for item in board.GetTracks()):
        raise RuntimeError("organicize must start from the angular routed source, not an already rounded PCB")
    if len(board.Zones()):
        raise RuntimeError("organicize must start from a routed source without copper zones")

    runner = _RoundRunner(board)

    def radius_for_intersection(corner_key) -> float:
        return ROUND_RADIUS_LEVELS_MM[radius_indexes.get(corner_key, 0)]

    RoundTracks.addIntermediateTracks(
        runner,
        scaling=ROUND_RADIUS_LEVELS_MM[0],
        netclass="Default",
        native=True,
        onlySelection=False,
        avoid_junctions=True,
        radius_for_intersection=radius_for_intersection,
    )
    return board, runner.created_arcs


def _nearest_arc(arc_records, net: str, x_mm: float, y_mm: float):
    candidates = [record for record in arc_records if record[0].GetNetname() == net]
    if not candidates:
        return None

    def distance(record) -> float:
        position = record[0].GetPosition()
        return (
            (pcbnew.ToMM(position.x) - x_mm) ** 2
            + (pcbnew.ToMM(position.y) - y_mm) ** 2
        )

    return min(candidates, key=distance)


def _fit_adaptive_radii(source: Path, kicad_cli: Path, workspace: Path):
    radius_indexes = {}
    candidate_board = workspace / "radius-candidate.kicad_pcb"
    report_path = workspace / "radius-candidate-drc.rpt"

    for iteration in range(16):
        board, arc_records = _rounded_board(source, radius_indexes)
        pcbnew.SaveBoard(str(candidate_board), board)
        categories = _drc_categories(kicad_cli, candidate_board, report_path)
        if not categories:
            return board, arc_records

        report = report_path.read_text(encoding="utf-8")
        offenders = []
        for x, y, net in ARC_REPORT.findall(report):
            record = _nearest_arc(arc_records, net, float(x), float(y))
            if record is not None:
                offenders.append(record[1])

        unique_keys = set(offenders)
        if not unique_keys:
            raise RuntimeError(
                f"cannot map adaptive-radius DRC categories: {sorted(set(categories))}"
            )

        for corner_key in unique_keys:
            next_index = radius_indexes.get(corner_key, 0) + 1
            if next_index >= len(ROUND_RADIUS_LEVELS_MM):
                raise RuntimeError(f"corner remains invalid at minimum radius: {corner_key}")
            radius_indexes[corner_key] = next_index
        print(
            f"adaptive radius pass {iteration + 1}: reduced {len(unique_keys)} corners"
        )

    raise RuntimeError("adaptive radius fitting did not converge")


def _node_map(board: pcbnew.BOARD) -> dict:
    nodes = {}
    for item in _copper_items(board):
        for point in (item.GetStart(), item.GetEnd()):
            key = (item.GetNetCode(), item.GetLayer(), point.x, point.y)
            nodes.setdefault(key, []).append(item)
    return nodes


def _normalize_transition_nodes(board: pcbnew.BOARD) -> None:
    narrow = pcbnew.FromMM(MIN_WIDTH_MM)
    wide = pcbnew.FromMM(PREFERRED_WIDTH_MM)

    while True:
        changed = False
        for items in _node_map(board).values():
            widths = {item.GetWidth() for item in items}
            if widths != {narrow, wide}:
                continue
            straight_items = [item for item in items if item.GetClass() == "PCB_TRACK"]
            if len(items) > 2 or not straight_items:
                for item in items:
                    item.SetWidth(narrow)
                changed = True
        if not changed:
            return


def _add_polygon_zone(board: pcbnew.BOARD, points, source, priority: int) -> None:
    zone = pcbnew.ZONE(board)
    zone.SetLayer(source.GetLayer())
    zone.SetNetCode(source.GetNetCode())
    zone.SetLocalClearance(source.GetLocalClearance(source.GetClass()))
    zone.SetMinThickness(25400)
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetCornerSmoothingType(pcbnew.ZONE_SETTINGS.SMOOTHING_NONE)
    zone.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
    zone.SetIsFilled(True)
    zone.SetAssignedPriority(priority)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in points:
        outline.Append(int(x), int(y))
    board.Add(zone)


def _add_width_tapers(board: pcbnew.BOARD) -> int:
    _normalize_transition_nodes(board)
    narrow = pcbnew.FromMM(MIN_WIDTH_MM)
    wide = pcbnew.FromMM(PREFERRED_WIDTH_MM)
    transition_nodes = []
    for key, items in _node_map(board).items():
        if {item.GetWidth() for item in items} != {narrow, wide}:
            continue
        wide_straights = [
            item for item in items
            if item.GetWidth() == wide and item.GetClass() == "PCB_TRACK"
        ]
        narrow_straights = [
            item for item in items
            if item.GetWidth() == narrow and item.GetClass() == "PCB_TRACK"
        ]
        if wide_straights:
            transition_nodes.append((key, wide_straights[0], narrow, wide))
        elif narrow_straights:
            transition_nodes.append((key, narrow_straights[0], wide, narrow))

    count = 0
    for key, track, node_width, base_width in transition_nodes:
        node = pcbnew.VECTOR2I(key[2], key[3])
        if track.GetStart() == node:
            other = track.GetEnd()
            set_endpoint = track.SetStart
        elif track.GetEnd() == node:
            other = track.GetStart()
            set_endpoint = track.SetEnd
        else:
            continue

        dx = other.x - node.x
        dy = other.y - node.y
        length = math.hypot(dx, dy)
        taper_length = min(pcbnew.FromMM(TAPER_LENGTH_MM), int(length * 0.35))
        if taper_length < pcbnew.FromMM(0.30):
            track.SetWidth(narrow)
            continue

        ux = dx / length
        uy = dy / length
        nx = -uy
        ny = ux
        base = pcbnew.VECTOR2I(
            int(node.x + ux * taper_length),
            int(node.y + uy * taper_length),
        )
        set_endpoint(base)

        left = []
        right = []
        for sample in range(9):
            t = sample / 8
            smooth = t * t * (3 - 2 * t)
            half_width = node_width / 2 + (base_width - node_width) * smooth / 2
            cx = node.x + ux * taper_length * t
            cy = node.y + uy * taper_length * t
            left.append((cx + nx * half_width, cy + ny * half_width))
            right.append((cx - nx * half_width, cy - ny * half_width))

        _add_polygon_zone(
            board,
            left + list(reversed(right)),
            track,
            priority=10 + count,
        )
        count += 1
    return count


def _add_teardrops(board: pcbnew.BOARD) -> int:
    count = SetTeardrops(
        hpercent=30,
        vpercent=65,
        segs=8,
        pcb=board,
        use_smd=True,
        discard_in_same_zone=False,
        follow_tracks=True,
        noBulge=True,
    )
    # The helper marks every new teardrop with priority 0x4242. Preserve the
    # lower taper priorities and make every pad teardrop priority unique.
    priority = 100
    for zone in board.Zones():
        if zone.GetAssignedPriority() == 0x4242:
            zone.SetAssignedPriority(priority)
            priority += 1
    return count


def _set_project_width_defaults(board: pcbnew.BOARD) -> None:
    preferred = pcbnew.FromMM(PREFERRED_WIDTH_MM)
    for netclass in board.GetAllNetClasses().values():
        netclass.SetTrackWidth(preferred)
    widths = pcbnew.intVector()
    widths.append(pcbnew.FromMM(MIN_WIDTH_MM))
    widths.append(preferred)
    board.GetDesignSettings().m_TrackWidthList = widths


def organicize(board_path: Path, kicad_cli: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="attiny1624-organic-") as temporary:
        workspace = Path(temporary)
        board, arc_records = _fit_adaptive_radii(board_path, kicad_cli, workspace)
        _fit_wide_tracks(board, kicad_cli, workspace)
        tapers = _add_width_tapers(board)
        teardrops = _add_teardrops(board)
        _set_project_width_defaults(board)
        pcbnew.SaveBoard(str(board_path), board)

        final_report = workspace / "final-drc.rpt"
        categories = _drc_categories(kicad_cli, board_path, final_report)
        if categories:
            raise RuntimeError(f"organic board has DRC categories: {sorted(set(categories))}")
        verified_board = pcbnew.LoadBoard(str(board_path))
        unconnected = verified_board.GetConnectivity().GetUnconnectedCount(False)
        if unconnected:
            raise RuntimeError(f"organic board has {unconnected} unconnected items")

    items = _copper_items(board)
    wide = pcbnew.FromMM(PREFERRED_WIDTH_MM)
    total_length = sum(item.GetLength() for item in items)
    wide_length = sum(item.GetLength() for item in items if item.GetWidth() == wide)
    arcs = sum(item.GetClass() == "PCB_ARC" for item in items)
    radius_limits = sorted({record[2] for record in arc_records})
    print(
        f"OK: {arcs} native arcs using {len(radius_limits)} adaptive limits "
        f"({radius_limits[0]:.2f}-{radius_limits[-1]:.2f} mm), {tapers} width tapers, "
        f"{teardrops} pad teardrops, "
        f"{100 * wide_length / total_length:.1f}% of routed length at 20 mil"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, required=True)
    parser.add_argument("--kicad-cli", type=Path, required=True)
    args = parser.parse_args()
    organicize(args.board, args.kicad_cli)


if __name__ == "__main__":
    main()
