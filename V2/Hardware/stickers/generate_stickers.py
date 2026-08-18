#!/usr/bin/env python3
"""Generate manufacturing-ready sticker sheets from a 64-character profile."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Sequence

from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


STICKERS_DIR = Path(__file__).resolve().parent
V2_DIR = STICKERS_DIR.parents[1]
CODE_DIR = V2_DIR / "Code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from character_sets import (  # noqa: E402
    CharacterSet,
    CharacterSetError,
    load_catalog,
    load_presets,
    resolve_character_set,
)


COLOR_PRESETS = {
    "black-white": ("#000000", "#FFFFFF"),
    "black-yellow": ("#000000", "#FFCC00"),
    "yellow-black": ("#FFCC00", "#000000"),
    "white-black": ("#FFFFFF", "#000000"),
}
DEFAULT_COLOR_PRESET = "black-white"
DEFAULT_FONT = STICKERS_DIR / "fonts" / "Blue Highway D.otf"
DEFAULT_FALLBACK_FONTS = (STICKERS_DIR / "fonts" / "Dream Orphans Bd.otf",)
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class StickerError(ValueError):
    """Raised when a sticker sheet cannot be generated safely."""


@dataclass(frozen=True)
class SheetGeometry:
    card_width_mm: float = 55.0
    card_height_mm: float = 86.0
    margin_mm: float = 5.0
    gap_mm: float = 4.0
    columns: int = 8
    glyph_padding_x_mm: float = 4.0
    cap_height_mm: float = 67.0
    split_y_mm: float = 43.0
    split_width_mm: float = 0.8
    guide_width_mm: float = 0.15

    def page_size(self, count: int) -> tuple[float, float, int]:
        if self.columns < 1:
            raise StickerError("columns must be at least 1")
        rows = math.ceil(count / self.columns)
        width = (
            2 * self.margin_mm
            + self.columns * self.card_width_mm
            + max(0, self.columns - 1) * self.gap_mm
        )
        height = (
            2 * self.margin_mm
            + rows * self.card_height_mm
            + max(0, rows - 1) * self.gap_mm
        )
        return width, height, rows


@dataclass
class FontFace:
    path: Path
    font: TTFont
    family: str
    style: str
    sha256: str
    cap_height: int
    cmap: dict[int, str]

    @classmethod
    def load(cls, path: Path) -> "FontFace":
        path = path.expanduser().resolve()
        if not path.is_file():
            raise StickerError(f"font file not found: {path}")
        font = TTFont(path)
        cmap = font.getBestCmap() or {}
        family = font["name"].getDebugName(1) or path.stem
        style = font["name"].getDebugName(2) or "Regular"
        cap_height = getattr(font["OS/2"], "sCapHeight", 0)
        if not cap_height:
            glyph_set = font.getGlyphSet()
            pen = BoundsPen(glyph_set)
            glyph_set[cmap[ord("H")]].draw(pen)
            if not pen.bounds:
                raise StickerError(f"cannot determine cap height for {path}")
            cap_height = round(pen.bounds[3] - pen.bounds[1])
        return cls(
            path=path,
            font=font,
            family=family,
            style=style,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            cap_height=cap_height,
            cmap=cmap,
        )

    @property
    def label(self) -> str:
        return f"{self.family} {self.style}".strip()

    def has(self, character: str) -> bool:
        return ord(character) in self.cmap

    def glyph_name(self, character: str) -> str:
        return self.cmap[ord(character)]


@dataclass(frozen=True)
class GlyphPlacement:
    character: str
    face: FontFace
    glyph_name: str
    path_data: str
    x_mm: float
    baseline_y_mm: float
    scale_x: float
    scale_y: float


def normalize_color(value: str) -> str:
    if not HEX_COLOR_RE.fullmatch(value):
        raise StickerError(f"color must use #RRGGBB notation; got {value!r}")
    return value.upper()


def resolve_colors(
    preset: str = DEFAULT_COLOR_PRESET,
    background: str | None = None,
    foreground: str | None = None,
) -> tuple[str, str]:
    try:
        preset_background, preset_foreground = COLOR_PRESETS[preset]
    except KeyError as error:
        raise StickerError(f"unknown color preset: {preset!r}") from error
    return (
        normalize_color(background or preset_background),
        normalize_color(foreground or preset_foreground),
    )


def select_face(character: str, faces: Sequence[FontFace]) -> FontFace:
    for face in faces:
        if face.has(character):
            return face
    names = ", ".join(face.label for face in faces)
    raise StickerError(f"no configured font contains {character!r}: {names}")


def glyph_placement(
    character: str,
    face: FontFace,
    card_x: float,
    card_y: float,
    geometry: SheetGeometry,
) -> GlyphPlacement:
    glyph_set = face.font.getGlyphSet()
    glyph_name = face.glyph_name(character)
    glyph = glyph_set[glyph_name]

    bounds_pen = BoundsPen(glyph_set)
    glyph.draw(bounds_pen)
    if not bounds_pen.bounds:
        raise StickerError(f"glyph {character!r} has no visible outline")
    x_min, y_min, x_max, y_max = bounds_pen.bounds

    svg_pen = SVGPathPen(glyph_set)
    glyph.draw(svg_pen)
    path_data = svg_pen.getCommands()

    scale_y = geometry.cap_height_mm / face.cap_height
    glyph_width_mm = (x_max - x_min) * scale_y
    max_width_mm = geometry.card_width_mm - 2 * geometry.glyph_padding_x_mm
    scale_x = scale_y * min(1.0, max_width_mm / glyph_width_mm)

    transformed_width = (x_max - x_min) * scale_x
    x_mm = card_x + (geometry.card_width_mm - transformed_width) / 2 - x_min * scale_x

    cap_top = card_y + (geometry.card_height_mm - geometry.cap_height_mm) / 2
    baseline_y_mm = cap_top + face.cap_height * scale_y
    visible_top = baseline_y_mm - y_max * scale_y
    visible_bottom = baseline_y_mm - y_min * scale_y
    min_y = card_y + 3.0
    max_y = card_y + geometry.card_height_mm - 3.0
    if visible_top < min_y:
        baseline_y_mm += min_y - visible_top
    if visible_bottom > max_y:
        baseline_y_mm -= visible_bottom - max_y

    return GlyphPlacement(
        character=character,
        face=face,
        glyph_name=glyph_name,
        path_data=path_data,
        x_mm=x_mm,
        baseline_y_mm=baseline_y_mm,
        scale_x=scale_x,
        scale_y=scale_y,
    )


def card_origin(index: int, geometry: SheetGeometry) -> tuple[float, float, int, int]:
    row, column = divmod(index, geometry.columns)
    x = geometry.margin_mm + column * (geometry.card_width_mm + geometry.gap_mm)
    y = geometry.margin_mm + row * (geometry.card_height_mm + geometry.gap_mm)
    return x, y, row, column


def xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def build_svg(
    profile: CharacterSet,
    faces: Sequence[FontFace],
    geometry: SheetGeometry,
    background: str,
    foreground: str,
    guide_color: str,
    include_guides: bool,
    omit_blank: bool,
) -> tuple[str, list[dict[str, Any]]]:
    characters = [character for character in profile.characters if not (omit_blank and character == " ")]
    page_width, page_height, _ = geometry.page_size(len(characters))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{number(page_width)}mm" '
            f'height="{number(page_height)}mm" viewBox="0 0 {number(page_width)} '
            f'{number(page_height)}">'
        ),
        f'  <title>{xml_escape(profile.name)} sticker sheet</title>',
        "  <g id=\"backgrounds\">",
    ]
    positions: list[dict[str, Any]] = []
    placements: list[GlyphPlacement | None] = []

    for sheet_index, character in enumerate(characters):
        x, y, row, column = card_origin(sheet_index, geometry)
        lines.append(
            f'    <rect id="card-{sheet_index + 1:02d}" x="{number(x)}" y="{number(y)}" '
            f'width="{number(geometry.card_width_mm)}" height="{number(geometry.card_height_mm)}" '
            f'fill="{background}"/>'
        )
        placement = None
        font_label = None
        if character != " ":
            face = select_face(character, faces)
            placement = glyph_placement(character, face, x, y, geometry)
            font_label = face.label
        placements.append(placement)
        positions.append(
            {
                "sheet_position": sheet_index + 1,
                "drum_position": profile.characters.index(character),
                "character": character,
                "row": row + 1,
                "column": column + 1,
                "font": font_label,
            }
        )
    lines.append("  </g>")
    lines.append(f'  <g id="glyphs" fill="{foreground}">')
    for sheet_index, placement in enumerate(placements):
        if placement is None:
            continue
        lines.append(
            f'    <path id="glyph-{sheet_index + 1:02d}" data-character="{xml_escape(placement.character)}" '
            f'd="{placement.path_data}" transform="translate({number(placement.x_mm)} '
            f'{number(placement.baseline_y_mm)}) scale({number(placement.scale_x)} '
            f'-{number(placement.scale_y)})"/>'
        )
    lines.append("  </g>")

    lines.append(f'  <g id="split-lines" fill="{background}">')
    for sheet_index in range(len(characters)):
        x, y, _, _ = card_origin(sheet_index, geometry)
        lines.append(
            f'    <rect x="{number(x)}" y="{number(y + geometry.split_y_mm - geometry.split_width_mm / 2)}" '
            f'width="{number(geometry.card_width_mm)}" height="{number(geometry.split_width_mm)}"/>'
        )
    lines.append("  </g>")

    if include_guides:
        lines.append(
            f'  <g id="cut-guides" fill="none" stroke="{guide_color}" '
            f'stroke-width="{number(geometry.guide_width_mm)}">'
        )
        for sheet_index in range(len(characters)):
            x, y, _, _ = card_origin(sheet_index, geometry)
            lines.append(
                f'    <rect x="{number(x)}" y="{number(y)}" width="{number(geometry.card_width_mm)}" '
                f'height="{number(geometry.card_height_mm)}"/>'
            )
            lines.append(
                f'    <path d="M {number(x)} {number(y + geometry.split_y_mm)} '
                f'H {number(x + geometry.card_width_mm)}"/>'
            )
        lines.append("  </g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n", positions


class CanvasPathPen(BasePen):
    """Small fontTools-compatible pen that writes into a ReportLab PDF path."""

    def __init__(self, glyph_set: Any, pdf_path: Any):
        super().__init__(glyph_set)
        self.path = pdf_path

    def _moveTo(self, point: tuple[float, float]) -> None:
        self.path.moveTo(*point)

    def _lineTo(self, point: tuple[float, float]) -> None:
        self.path.lineTo(*point)

    def _curveToOne(
        self,
        point1: tuple[float, float],
        point2: tuple[float, float],
        point3: tuple[float, float],
    ) -> None:
        flattened = [
            coordinate
            for point in (point1, point2, point3)
            for coordinate in point
        ]
        self.path.curveTo(*flattened)

    def _closePath(self) -> None:
        self.path.close()

    def _endPath(self) -> None:
        pass


def write_pdf(
    output: Path,
    profile: CharacterSet,
    faces: Sequence[FontFace],
    geometry: SheetGeometry,
    background: str,
    foreground: str,
    guide_color: str,
    include_guides: bool,
    omit_blank: bool,
) -> None:
    characters = [character for character in profile.characters if not (omit_blank and character == " ")]
    page_width, page_height, _ = geometry.page_size(len(characters))
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(
        str(output),
        pagesize=(page_width * mm, page_height * mm),
        pageCompression=1,
        invariant=1,
    )
    pdf.setTitle(f"{profile.name} sticker sheet")
    pdf.setAuthor("Alphabets sticker generator")

    pdf.setFillColor(HexColor(background))
    for index in range(len(characters)):
        x, y_top, _, _ = card_origin(index, geometry)
        y = page_height - y_top - geometry.card_height_mm
        pdf.rect(x * mm, y * mm, geometry.card_width_mm * mm, geometry.card_height_mm * mm, fill=1, stroke=0)

    pdf.setFillColor(HexColor(foreground))
    for index, character in enumerate(characters):
        if character == " ":
            continue
        x, y_top, _, _ = card_origin(index, geometry)
        face = select_face(character, faces)
        placement = glyph_placement(character, face, x, y_top, geometry)
        glyph_set = face.font.getGlyphSet()
        pdf_path = pdf.beginPath()
        glyph_set[placement.glyph_name].draw(CanvasPathPen(glyph_set, pdf_path))
        pdf.saveState()
        pdf.translate(placement.x_mm * mm, (page_height - placement.baseline_y_mm) * mm)
        pdf.scale(placement.scale_x * mm, placement.scale_y * mm)
        pdf.drawPath(pdf_path, fill=1, stroke=0)
        pdf.restoreState()

    pdf.setFillColor(HexColor(background))
    for index in range(len(characters)):
        x, y_top, _, _ = card_origin(index, geometry)
        y = page_height - y_top - geometry.split_y_mm - geometry.split_width_mm / 2
        pdf.rect(x * mm, y * mm, geometry.card_width_mm * mm, geometry.split_width_mm * mm, fill=1, stroke=0)

    if include_guides:
        pdf.setStrokeColor(HexColor(guide_color))
        pdf.setLineWidth(geometry.guide_width_mm * mm)
        for index in range(len(characters)):
            x, y_top, _, _ = card_origin(index, geometry)
            y = page_height - y_top - geometry.card_height_mm
            pdf.rect(x * mm, y * mm, geometry.card_width_mm * mm, geometry.card_height_mm * mm, fill=0, stroke=1)
            split_y = page_height - y_top - geometry.split_y_mm
            pdf.line(x * mm, split_y * mm, (x + geometry.card_width_mm) * mm, split_y * mm)

    pdf.showPage()
    pdf.save()


def build_manifest(
    profile: CharacterSet,
    faces: Sequence[FontFace],
    positions: list[dict[str, Any]],
    geometry: SheetGeometry,
    color_preset: str,
    background: str,
    foreground: str,
    guide_color: str,
    include_guides: bool,
    omit_blank: bool,
) -> dict[str, Any]:
    page_width, page_height, rows = geometry.page_size(len(positions))
    return {
        "schema_version": 1,
        "generator": "generate_stickers.py",
        "character_set": {
            "id": profile.id,
            "name": profile.name,
            "characters": profile.characters,
        },
        "colors": {
            "preset": color_preset,
            "background": background,
            "foreground": foreground,
            "guide": guide_color if include_guides else None,
        },
        "geometry_mm": {
            "card": [geometry.card_width_mm, geometry.card_height_mm],
            "page": [page_width, page_height],
            "margin": geometry.margin_mm,
            "gap": geometry.gap_mm,
            "split_y": geometry.split_y_mm,
            "columns": geometry.columns,
            "rows": rows,
        },
        "omit_blank": omit_blank,
        "fonts": [
            {
                "role": "primary" if index == 0 else "fallback",
                "file": face.path.name,
                "family": face.family,
                "style": face.style,
                "sha256": face.sha256,
            }
            for index, face in enumerate(faces)
        ],
        "positions": positions,
    }


def load_profile(preset: str | None, settings: Path | None) -> CharacterSet:
    if settings:
        with settings.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return resolve_character_set(data)
    if preset:
        presets = load_presets()
        try:
            return presets[preset]
        except KeyError as error:
            raise StickerError(f"unknown character preset: {preset!r}") from error
    catalog = load_catalog()
    return load_presets()[catalog["default_preset"]]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--preset", help="character preset id (default: catalog default)")
    source.add_argument("--settings", type=Path, help="settings JSON with preset or custom characters")
    parser.add_argument("--color-preset", choices=sorted(COLOR_PRESETS), default=DEFAULT_COLOR_PRESET)
    parser.add_argument("--background", help="background override in #RRGGBB notation")
    parser.add_argument("--foreground", help="letter-color override in #RRGGBB notation")
    parser.add_argument("--guide-color", default="#FF00FF", help="cut-guide color in #RRGGBB notation")
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT, help="primary OpenType font")
    parser.add_argument("--fallback-font", action="append", type=Path, dest="fallback_fonts", help="fallback OpenType font; may be repeated")
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--omit-blank", action="store_true", help="omit the blank drum position")
    parser.add_argument("--no-guides", action="store_true", help="omit cut outlines and center lines")
    parser.add_argument("--output-svg", type=Path, required=True)
    parser.add_argument("--output-pdf", type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        profile = load_profile(args.preset, args.settings)
        background, foreground = resolve_colors(args.color_preset, args.background, args.foreground)
        guide_color = normalize_color(args.guide_color)
        fallback_paths = tuple(args.fallback_fonts) if args.fallback_fonts is not None else DEFAULT_FALLBACK_FONTS
        faces = [FontFace.load(args.font), *(FontFace.load(path) for path in fallback_paths)]
        for character in profile.characters:
            if character != " ":
                select_face(character, faces)
        geometry = SheetGeometry(columns=args.columns)
        svg, positions = build_svg(
            profile, faces, geometry, background, foreground, guide_color,
            not args.no_guides, args.omit_blank,
        )
        args.output_svg.parent.mkdir(parents=True, exist_ok=True)
        args.output_svg.write_text(svg, encoding="utf-8")
        if args.output_pdf:
            write_pdf(
                args.output_pdf, profile, faces, geometry, background, foreground,
                guide_color, not args.no_guides, args.omit_blank,
            )
        manifest_path = args.manifest or args.output_svg.with_suffix(".json")
        manifest = build_manifest(
            profile, faces, positions, geometry, args.color_preset, background,
            foreground, guide_color, not args.no_guides, args.omit_blank,
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (StickerError, CharacterSetError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
