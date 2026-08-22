#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Generate a variant-locked V2 split-flap card and cutter files.

Run this script with FreeCADCmd, not the system Python interpreter.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shlex
import sys
from xml.sax.saxutils import escape

import FreeCAD as App
import Part


CARDS_DIR = Path(__file__).resolve().parent
V2_DIR = CARDS_DIR.parents[1]
CODE_DIR = V2_DIR / "Code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from physical_variants import PhysicalVariantError, load_variant  # noqa: E402


DRUM_DIAMETER_MM = 85.0
DRUM_SIDE_THICKNESS_MM = 2.15
DRUM_POSITIONS = 64
FLAP_HOLE_DIAMETER_MM = 3.0
FLAP_ROTATION_CLEARANCE_MM = 0.15
CUT_COLOR = "#FF00FF"
CUT_WIDTH_MM = 0.15
SVG_MARGIN_MM = 1.0


def number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def card_points(
    body_width_mm: float,
    total_height_mm: float,
    tab_width_mm: float,
    tab_height_mm: float,
) -> list[tuple[float, float]]:
    body_height_mm = total_height_mm - tab_height_mm
    return [
        (0.0, 0.0),
        (body_width_mm, 0.0),
        (body_width_mm, body_height_mm),
        (body_width_mm + tab_width_mm, body_height_mm),
        (body_width_mm + tab_width_mm, total_height_mm),
        (-tab_width_mm, total_height_mm),
        (-tab_width_mm, body_height_mm),
        (0.0, body_height_mm),
    ]


def validate_dimensions(args: argparse.Namespace) -> None:
    values = {
        "body width": args.body_width,
        "total height": args.total_height,
        "tab width": args.tab_width,
        "tab height": args.tab_height,
        "thickness": args.thickness,
        "sticker width": args.sticker_width,
        "sticker face height": args.sticker_face_height,
        "sticker face thickness": args.sticker_face_thickness,
        "axial clearance": args.axial_clearance,
    }
    for label, value in values.items():
        if value <= 0:
            raise ValueError(f"{label} must be positive")
    if args.tab_height >= args.total_height:
        raise ValueError("tab height must be smaller than total height")
    if args.sticker_width >= args.body_width:
        raise ValueError("sticker width must leave a lateral placement margin")
    if args.sticker_face_height != args.total_height - args.tab_height:
        raise ValueError("sticker face height must end where the lateral tabs begin")
    if args.variant == "definitive":
        tab_corner_radius = math.hypot(args.tab_height / 2, args.thickness / 2)
        usable_hole_radius = FLAP_HOLE_DIAMETER_MM / 2 - FLAP_ROTATION_CLEARANCE_MM
        if tab_corner_radius > usable_hole_radius:
            raise ValueError(
                "definitive card tab cannot rotate in the 3 mm drum hole with "
                "the required 0.15 mm radial clearance"
            )


def add_parameter_sheet(doc: App.Document, args: argparse.Namespace) -> None:
    sheet = doc.addObject("Spreadsheet::Sheet", "Parameters")
    sheet.Label = "Card parameters"
    rows = [
        ("Body width", args.body_width, "body_width"),
        ("Total height", args.total_height, "total_height"),
        ("Tab width", args.tab_width, "tab_width"),
        ("Tab height", args.tab_height, "tab_height"),
        ("Material thickness", args.thickness, "material_thickness"),
        ("Sticker width", args.sticker_width, "sticker_width"),
        ("Sticker face height", args.sticker_face_height, "sticker_face_height"),
        (
            "Sticker face thickness",
            args.sticker_face_thickness,
            "sticker_face_thickness",
        ),
        (
            "Finished thickness",
            args.thickness + 2 * args.sticker_face_thickness,
            "finished_thickness",
        ),
        ("Axial clearance", args.axial_clearance, "axial_clearance"),
        (
            "Drum inner width",
            args.body_width + args.axial_clearance,
            "drum_inner_width",
        ),
    ]
    for row, (label, value, alias) in enumerate(rows, start=1):
        sheet.set(f"A{row}", label)
        sheet.set(f"B{row}", f"{number(value)} mm")
        sheet.setAlias(f"B{row}", alias)
    sheet.set("B9", "=material_thickness + 2 * sticker_face_thickness")
    sheet.set("B11", "=body_width + axial_clearance")
    sheet.setColumnWidth("A", 190)
    sheet.setColumnWidth("B", 100)


def build_fcstd(output: Path, args: argparse.Namespace) -> None:
    stem = f"V2Card{number(args.body_width)}x{number(args.total_height)}"
    doc = App.newDocument(stem)
    doc.Label = f"{args.variant_name} card {number(args.body_width)} x {number(args.total_height)} mm"
    doc.CreatedBy = "The Beach Lab"
    doc.Company = "The Beach Lab"
    doc.License = "MIT"
    doc.LicenseURL = "https://github.com/TheBeachLab/alphabets/blob/master/LICENSE"
    doc.Comment = (
        "SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>. "
        "SPDX-License-" "Identifier: MIT. "
        f"Matched to the {number(args.body_width)} x {number(args.total_height * 2)} mm "
        f"{args.variant_name} sticker and {number(args.body_width + args.axial_clearance)} mm drum."
    )
    add_parameter_sheet(doc, args)

    points = card_points(
        args.body_width,
        args.total_height,
        args.tab_width,
        args.tab_height,
    )
    vectors = [App.Vector(x, y, 0) for x, y in points]
    vectors.append(vectors[0])
    wire = Part.makePolygon(vectors)

    outline = doc.addObject("Part::Feature", "CutOutline")
    outline.Label = "Card cut outline"
    outline.Shape = wire
    outline.addProperty("App::PropertyString", "CutLayer", "Manufacturing")
    outline.CutLayer = "CUT"

    body = doc.addObject("Part::Box", "Body")
    body.Label = "Visible card body"
    body.Length = args.body_width
    body.Width = args.total_height - args.tab_height
    body.Height = args.thickness
    body.setExpression("Length", "Parameters.body_width")
    body.setExpression("Width", "Parameters.total_height - Parameters.tab_height")
    body.setExpression("Height", "Parameters.material_thickness")

    tab_band = doc.addObject("Part::Box", "TabBand")
    tab_band.Label = "Card tab band"
    tab_band.Length = args.body_width + 2 * args.tab_width
    tab_band.Width = args.tab_height
    tab_band.Height = args.thickness
    tab_band.Placement.Base = App.Vector(
        -args.tab_width,
        args.total_height - args.tab_height,
        0,
    )
    tab_band.setExpression("Length", "Parameters.body_width + 2 * Parameters.tab_width")
    tab_band.setExpression("Width", "Parameters.tab_height")
    tab_band.setExpression("Height", "Parameters.material_thickness")
    tab_band.setExpression("Placement.Base.x", "-Parameters.tab_width")
    tab_band.setExpression(
        "Placement.Base.y", "Parameters.total_height - Parameters.tab_height"
    )

    solid = doc.addObject("Part::MultiFuse", "Card")
    solid.Label = f"Card {number(args.body_width)} x {number(args.total_height)}"
    solid.Shapes = [body, tab_band]
    solid.Refine = True
    for name, label, value, expression in (
        ("BodyWidth", "Body width", args.body_width, "Parameters.body_width"),
        ("TotalHeight", "Total height", args.total_height, "Parameters.total_height"),
        ("TabWidth", "Tab width", args.tab_width, "Parameters.tab_width"),
        ("TabHeight", "Tab height", args.tab_height, "Parameters.tab_height"),
        (
            "MaterialThickness",
            "Material thickness",
            args.thickness,
            "Parameters.material_thickness",
        ),
        (
            "StickerWidth",
            "Sticker width",
            args.sticker_width,
            "Parameters.sticker_width",
        ),
        (
            "StickerFaceHeight",
            "Sticker height on each face",
            args.sticker_face_height,
            "Parameters.sticker_face_height",
        ),
        (
            "StickerFaceThickness",
            "Sticker thickness on each face",
            args.sticker_face_thickness,
            "Parameters.sticker_face_thickness",
        ),
        (
            "FinishedThickness",
            "Finished body thickness",
            args.thickness + 2 * args.sticker_face_thickness,
            "Parameters.finished_thickness",
        ),
        (
            "DrumInnerWidth",
            "Matching drum inner width",
            args.body_width + args.axial_clearance,
            "Parameters.drum_inner_width",
        ),
    ):
        solid.addProperty("App::PropertyLength", name, "Dimensions", label)
        setattr(solid, name, value)
        solid.setExpression(name, expression)

    front_sticker = doc.addObject("Part::Box", "FrontSticker")
    front_sticker.Label = "Front sticker layer"
    front_sticker.Length = args.sticker_width
    front_sticker.Width = args.sticker_face_height
    front_sticker.Height = args.sticker_face_thickness
    sticker_x = (args.body_width - args.sticker_width) / 2
    sticker_y = args.total_height - args.sticker_face_height
    front_sticker.Placement.Base = App.Vector(
        sticker_x, sticker_y, -args.sticker_face_thickness
    )
    front_sticker.setExpression("Length", "Parameters.sticker_width")
    front_sticker.setExpression("Width", "Parameters.sticker_face_height")
    front_sticker.setExpression("Height", "Parameters.sticker_face_thickness")
    front_sticker.setExpression(
        "Placement.Base.x", "(Parameters.body_width - Parameters.sticker_width) / 2"
    )
    front_sticker.setExpression(
        "Placement.Base.y", "Parameters.total_height - Parameters.sticker_face_height"
    )
    front_sticker.setExpression(
        "Placement.Base.z", "-Parameters.sticker_face_thickness"
    )

    back_sticker = doc.addObject("Part::Box", "BackSticker")
    back_sticker.Label = "Back sticker layer"
    back_sticker.Length = args.sticker_width
    back_sticker.Width = args.sticker_face_height
    back_sticker.Height = args.sticker_face_thickness
    back_sticker.Placement.Base = App.Vector(sticker_x, sticker_y, args.thickness)
    back_sticker.setExpression("Length", "Parameters.sticker_width")
    back_sticker.setExpression("Width", "Parameters.sticker_face_height")
    back_sticker.setExpression("Height", "Parameters.sticker_face_thickness")
    back_sticker.setExpression(
        "Placement.Base.x", "(Parameters.body_width - Parameters.sticker_width) / 2"
    )
    back_sticker.setExpression(
        "Placement.Base.y", "Parameters.total_height - Parameters.sticker_face_height"
    )
    back_sticker.setExpression("Placement.Base.z", "Parameters.material_thickness")

    finished = doc.addObject("Part::MultiFuse", "FinishedCard")
    finished.Label = "Card with two sticker layers"
    finished.Shapes = [solid, front_sticker, back_sticker]
    finished.Refine = True
    black = (0.015, 0.015, 0.018)
    for feature in (front_sticker, back_sticker, finished):
        feature.addProperty(
            "App::PropertyString",
            "StickerColor",
            "Appearance",
            "Visible sticker colour",
        )
        feature.StickerColor = "#000000"
    for feature in (solid, front_sticker, back_sticker, finished):
        if feature.ViewObject is not None:
            feature.ViewObject.ShapeColor = black

    doc.recompute()
    output.parent.mkdir(parents=True, exist_ok=True)
    preferences = App.ParamGet("User parameter:BaseApp/Preferences/Document")
    backup_count = preferences.GetInt("CountBackupFiles", 2)
    preferences.SetInt("CountBackupFiles", 0)
    try:
        doc.saveAs(str(output.resolve()))
    finally:
        preferences.SetInt("CountBackupFiles", backup_count)
    App.closeDocument(doc.Name)


def build_svg(output: Path, args: argparse.Namespace) -> None:
    points = card_points(
        args.body_width,
        args.total_height,
        args.tab_width,
        args.tab_height,
    )
    shifted = [
        (
            x + args.tab_width + SVG_MARGIN_MM,
            args.total_height - y + SVG_MARGIN_MM,
        )
        for x, y in points
    ]
    commands = [f"M {number(shifted[0][0])} {number(shifted[0][1])}"]
    commands.extend(f"L {number(x)} {number(y)}" for x, y in shifted[1:])
    commands.append("Z")
    overall_width = args.body_width + 2 * args.tab_width
    canvas_width = overall_width + 2 * SVG_MARGIN_MM
    canvas_height = args.total_height + 2 * SVG_MARGIN_MM
    title = (
        f"V2 card {number(args.body_width)} x {number(args.total_height)} mm cut path"
    )
    svg = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{number(canvas_width)}mm" '
                f'height="{number(canvas_height)}mm" viewBox="0 0 {number(canvas_width)} '
                f'{number(canvas_height)}">'
            ),
            f"  <title>{escape(title)}</title>",
            (
                f'  <path id="card-cut" d="{" ".join(commands)}" fill="none" '
                f'stroke="{CUT_COLOR}" stroke-width="{number(CUT_WIDTH_MM)}"/>'
            ),
            "</svg>",
            "",
        ]
    )
    output.write_text(svg, encoding="utf-8")


def build_dxf(output: Path, args: argparse.Namespace) -> None:
    points = card_points(
        args.body_width,
        args.total_height,
        args.tab_width,
        args.tab_height,
    )
    lines = [
        "0",
        "SECTION",
        "2",
        "HEADER",
        "9",
        "$ACADVER",
        "1",
        "AC1015",
        "0",
        "ENDSEC",
        "0",
        "SECTION",
        "2",
        "ENTITIES",
        "0",
        "LWPOLYLINE",
        "8",
        "CUT",
        "90",
        str(len(points)),
        "70",
        "1",
    ]
    for x, y in points:
        lines.extend(["10", number(x), "20", number(y)])
    lines.extend(["0", "ENDSEC", "0", "EOF", ""])
    output.write_text("\n".join(lines), encoding="ascii")


def build_manifest(output: Path, args: argparse.Namespace) -> None:
    tab_corner_radius = math.hypot(args.tab_height / 2, args.thickness / 2)
    data = {
        "physical_variant": args.variant,
        "card_mm": {
            "body_width": args.body_width,
            "visible_height": args.total_height,
            "tab_start_height": args.total_height - args.tab_height,
            "total_height": args.total_height,
            "overall_width_with_tabs": args.body_width + 2 * args.tab_width,
            "tab_width": args.tab_width,
            "tab_height": args.tab_height,
            "material_thickness": args.thickness,
            "sticker_width": args.sticker_width,
            "sticker_face_height": args.sticker_face_height,
            "sticker_side_margin": (args.body_width - args.sticker_width) / 2,
            "sticker_y_offset": args.total_height - args.sticker_face_height,
            "sticker_face_thickness": args.sticker_face_thickness,
            "finished_thickness": args.thickness + 2 * args.sticker_face_thickness,
            "display_color_source": "sticker",
            "default_display_color": "#000000",
        },
        "matching_sticker_mm": [args.sticker_width, args.sticker_face_height * 2],
        "drum_mm": {
            "inner_width": args.body_width + args.axial_clearance,
            "axial_clearance": args.axial_clearance,
            "side_thickness": DRUM_SIDE_THICKNESS_MM,
            "outer_width": (
                args.body_width + args.axial_clearance + 2 * DRUM_SIDE_THICKNESS_MM
            ),
            "diameter": DRUM_DIAMETER_MM,
            "positions": DRUM_POSITIONS,
            "flap_hole_diameter": FLAP_HOLE_DIAMETER_MM,
            "tab_rotation_radius": tab_corner_radius,
            "tab_radial_clearance": FLAP_HOLE_DIAMETER_MM / 2 - tab_corner_radius,
        },
        "cut": {
            "layer": "CUT",
            "color": CUT_COLOR,
            "stroke_width_mm": CUT_WIDTH_MM,
            "svg_margin_mm": SVG_MARGIN_MM,
        },
    }
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--variant", choices=("prototype", "definitive"), default="definitive"
    )
    parser.add_argument("--body-width", type=float)
    parser.add_argument("--total-height", type=float)
    parser.add_argument("--tab-width", type=float)
    parser.add_argument("--tab-height", type=float)
    parser.add_argument("--thickness", type=float)
    parser.add_argument("--sticker-width", type=float)
    parser.add_argument("--sticker-face-height", type=float)
    parser.add_argument("--sticker-face-thickness", type=float)
    parser.add_argument("--axial-clearance", type=float)
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).resolve().parent
    )
    parser.add_argument("--stem")
    script = Path(__file__).resolve()
    argv = []
    for raw_argument in sys.argv[1:]:
        if raw_argument == "--pass":
            continue
        for argument in shlex.split(raw_argument):
            try:
                if Path(argument).resolve() == script:
                    continue
            except OSError:
                pass
            argv.append(argument)
    args = parser.parse_args(argv)
    variant = load_variant(args.variant)
    values = {
        "body_width": variant.card.body_width_mm,
        "total_height": variant.card.total_height_mm,
        "tab_width": variant.card.tab_width_mm,
        "tab_height": variant.card.tab_height_mm,
        "thickness": variant.card.material_thickness_mm,
        "sticker_width": variant.sticker.width_mm,
        "sticker_face_height": variant.sticker.split_y_mm,
        "sticker_face_thickness": variant.card.sticker_face_thickness_mm,
        "axial_clearance": variant.drum.inner_width_mm - variant.card.body_width_mm,
    }
    for field, expected in values.items():
        supplied = getattr(args, field)
        if supplied is not None and supplied != expected:
            parser.error(
                f"{variant.name} requires --{field.replace('_', '-')} {expected:g}"
            )
        setattr(args, field, expected)
    args.variant_name = variant.name
    if args.stem is None:
        args.stem = f"card-{number(args.body_width)}x{number(args.total_height)}"
    return args


def main() -> int:
    try:
        args = parse_args()
    except PhysicalVariantError as error:
        raise SystemExit(f"error: {error}") from error
    validate_dimensions(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    build_fcstd(args.output_dir / f"{args.stem}.fcstd", args)
    build_svg(args.output_dir / f"{args.stem}-cut.svg", args)
    build_dxf(args.output_dir / f"{args.stem}-cut.dxf", args)
    build_manifest(args.output_dir / f"{args.stem}.json", args)
    return 0


# FreeCADCmd executes scripts with a FreeCAD-specific module name rather than
# Python's conventional ``__main__``. This file is a command, not an importable
# library, so invoke it unconditionally.
main()
