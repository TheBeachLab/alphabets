#!/usr/bin/env python3
"""Create the wide, rounded, teardropped fabrication PCB from routed copper."""

from __future__ import annotations

import argparse
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
ROUND_RADIUS_MM = 0.20
IGNORED_DRC_CATEGORIES = {"lib_footprint_issues"}
TRACK_REPORT = re.compile(
    r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): Track(?: \(arc\))? \[([^]]+)\]"
)


class _Progress:
    def Pulse(self, *_args) -> bool:  # noqa: N802 - KiCad/wx naming
        return True


class _RoundRunner:
    def __init__(self, board: pcbnew.BOARD) -> None:
        self.board = board
        self.prog = _Progress()


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


def _round_tracks(board: pcbnew.BOARD) -> None:
    if any(item.GetClass() == "PCB_ARC" for item in board.GetTracks()):
        raise RuntimeError("organicize must start from the angular routed source, not an already rounded PCB")
    RoundTracks.addIntermediateTracks(
        _RoundRunner(board),
        scaling=ROUND_RADIUS_MM,
        netclass="Default",
        native=True,
        onlySelection=False,
        avoid_junctions=True,
    )


def _add_teardrops(board: pcbnew.BOARD) -> int:
    if len(board.Zones()):
        raise RuntimeError("organicize expects a routed source without copper zones")
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
    # The legacy geometry helper marks every teardrop with the same priority.
    # Unique priorities allow same-net teardrops to overlap without a KiCad DRC error.
    for priority, zone in enumerate(board.Zones(), start=100):
        zone.SetAssignedPriority(priority)
    return count


def organicize(board_path: Path, kicad_cli: Path) -> None:
    board = pcbnew.LoadBoard(str(board_path))
    _round_tracks(board)

    with tempfile.TemporaryDirectory(prefix="attiny44-organic-") as temporary:
        workspace = Path(temporary)
        _fit_wide_tracks(board, kicad_cli, workspace)
        teardrops = _add_teardrops(board)
        pcbnew.SaveBoard(str(board_path), board)

        final_report = workspace / "final-drc.rpt"
        categories = _drc_categories(kicad_cli, board_path, final_report)
        if categories:
            raise RuntimeError(f"organic board has DRC categories: {sorted(set(categories))}")

    items = _copper_items(board)
    wide = pcbnew.FromMM(PREFERRED_WIDTH_MM)
    total_length = sum(item.GetLength() for item in items)
    wide_length = sum(item.GetLength() for item in items if item.GetWidth() == wide)
    arcs = sum(item.GetClass() == "PCB_ARC" for item in items)
    print(
        f"OK: {arcs} native arcs, {teardrops} teardrops, "
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
