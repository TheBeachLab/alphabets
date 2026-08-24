#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Generate manufacturing-ready sticker sheets from a 64-character profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

STICKERS_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = STICKERS_DIR.parents[3]
LICENSES_DIR = REPOSITORY_ROOT / "LICENSES"
VARIANTS_DIR = REPOSITORY_ROOT / "V2/Hardware/variants"
for source_dir in (LICENSES_DIR, VARIANTS_DIR):
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

from artifact_license_metadata import (  # noqa: E402
    DEFAULT_LICENSE_TEXT,
    embed_artifact_license,
)
from character_sets import (  # noqa: E402
    CharacterSet,
    CharacterSetError,
    load_catalog,
    load_presets,
    resolve_character_set,
)
from json_license_metadata import write_licensed_json  # noqa: E402
from physical_variants import (  # noqa: E402
    PhysicalVariant,
    PhysicalVariantError,
    load_variant,
)

COLOR_PRESETS = {
    "black-white": ("#000000", "#FFFFFF"),
    "black-yellow": ("#000000", "#FFCC00"),
    "yellow-black": ("#FFCC00", "#000000"),
    "white-black": ("#FFFFFF", "#000000"),
}
DEFAULT_COLOR_PRESET = "black-white"
DEFAULT_FONT = STICKERS_DIR / "fonts" / "BlueHighwayD-International.otf"
DEFAULT_FONT_WEIGHT: float | None = None
DEFAULT_FONT_WIDTH: float | None = None
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class StickerError(ValueError):
    """Raised when a sticker sheet cannot be generated safely."""


@dataclass(frozen=True)
class SheetGeometry:
    card_width_mm: float = 55.0
    card_height_mm: float = 86.0
    margin_mm: float = 5.0
    column_gap_mm: float = 8.0
    row_gap_mm: float = 5.0
    columns: int = 22
    glyph_padding_x_mm: float = 0.0
    glyph_padding_y_mm: float = 0.0
    split_y_mm: float = 43.0
    cut_gap_mm: float = 0.0
    guide_width_mm: float = 0.15

    @property
    def artwork_height_mm(self) -> float:
        """Printed height across the two cut halves and their center gap."""

        return self.card_height_mm + self.cut_gap_mm

    def page_size(self, count: int) -> tuple[float, float, int]:
        if self.columns < 1:
            raise StickerError("columns must be at least 1")
        if self.card_width_mm <= 0 or self.card_height_mm <= 0:
            raise StickerError("card dimensions must be positive")
        if not 0 <= self.glyph_padding_x_mm < self.card_width_mm / 2:
            raise StickerError("horizontal glyph padding does not fit the card")
        if not 0 <= self.glyph_padding_y_mm < self.artwork_height_mm / 2:
            raise StickerError("vertical glyph padding does not fit the card")
        if not 0 < self.split_y_mm < self.card_height_mm:
            raise StickerError("split position must be inside the sticker height")
        if self.cut_gap_mm < 0:
            raise StickerError("cut gap cannot be negative")
        rows = math.ceil(count / self.columns)
        width = (
            2 * self.margin_mm
            + self.columns * self.card_width_mm
            + max(0, self.columns - 1) * self.column_gap_mm
        )
        height = (
            2 * self.margin_mm
            + rows * self.artwork_height_mm
            + max(0, rows - 1) * self.row_gap_mm
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
    variation_location: dict[str, float]

    @classmethod
    def load(
        cls,
        path: Path,
        weight: float | None = None,
        width: float | None = None,
    ) -> "FontFace":
        path = path.expanduser().resolve()
        if not path.is_file():
            raise StickerError(f"font file not found: {path}")
        font = TTFont(path)
        cmap = font.getBestCmap() or {}
        family = font["name"].getDebugName(1) or path.stem
        style = font["name"].getDebugName(2) or "Regular"
        variation_location: dict[str, float] = {}
        requested_axes = {"wght": weight, "wdth": width}
        if "fvar" in font:
            available_axes = {axis.axisTag: axis for axis in font["fvar"].axes}
            for tag, requested in requested_axes.items():
                if requested is None or tag not in available_axes:
                    continue
                axis = available_axes[tag]
                if not axis.minValue <= requested <= axis.maxValue:
                    raise StickerError(
                        f"font axis {tag!r} must be between {axis.minValue:g} "
                        f"and {axis.maxValue:g}; got {requested:g}"
                    )
                variation_location[tag] = requested
        if variation_location:
            style = " ".join(
                f"{tag} {value:g}" for tag, value in sorted(variation_location.items())
            )
        cap_height = getattr(font["OS/2"], "sCapHeight", 0)
        if not cap_height:
            glyph_set = font.getGlyphSet(location=variation_location or None)
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
            variation_location=variation_location,
        )

    @property
    def label(self) -> str:
        return f"{self.family} {self.style}".strip()

    def has(self, character: str) -> bool:
        return ord(character) in self.cmap

    def glyph_name(self, character: str) -> str:
        return self.cmap[ord(character)]

    def glyph_set(self) -> Any:
        return self.font.getGlyphSet(location=self.variation_location or None)


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


@dataclass(frozen=True)
class TypographyLayout:
    """One global x/y transform and baseline shared by the complete sheet."""

    scale_x: float
    scale_y: float
    baseline_in_card_mm: float
    source_bounds: tuple[float, float, float, float]
    advance_units_range: tuple[float, float]
    max_visible_width_units: float

    @property
    def advance_mm_range(self) -> tuple[float, float]:
        return tuple(value * self.scale_x for value in self.advance_units_range)

    @property
    def width_ratio(self) -> float:
        return self.scale_x / self.scale_y

    @property
    def is_monospaced(self) -> bool:
        return math.isclose(
            self.advance_units_range[0],
            self.advance_units_range[1],
            abs_tol=1e-6,
        )


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


def typography_layout(
    characters: str,
    face: FontFace,
    geometry: SheetGeometry,
) -> TypographyLayout:
    """Fit the whole preset once while preserving a common baseline and cell."""

    glyph_set = face.glyph_set()
    advances: list[float] = []
    bounds: list[tuple[float, float, float, float]] = []
    for character in characters:
        if character == " ":
            continue
        glyph = glyph_set[face.glyph_name(character)]
        advances.append(glyph.width)
        bounds_pen = BoundsPen(glyph_set)
        glyph.draw(bounds_pen)
        if not bounds_pen.bounds:
            raise StickerError(f"glyph {character!r} has no visible outline")
        bounds.append(bounds_pen.bounds)

    x_min = min(bound[0] for bound in bounds)
    y_min = min(bound[1] for bound in bounds)
    x_max = max(bound[2] for bound in bounds)
    y_max = max(bound[3] for bound in bounds)
    max_visible_width = max(bound[2] - bound[0] for bound in bounds)

    horizontal_scale = (
        geometry.card_width_mm - 2 * geometry.glyph_padding_x_mm
    ) / max_visible_width
    # Preserve the typeface geometry: width is the controlling dimension and
    # the same scale is applied on both axes. If a profile becomes too tall,
    # glyph_placement rejects it so the physical height can be changed rather
    # than silently deforming the artwork.
    scale_x = horizontal_scale
    scale_y = horizontal_scale

    baseline = geometry.artwork_height_mm / 2 + (y_max + y_min) * scale_y / 2
    return TypographyLayout(
        scale_x=scale_x,
        scale_y=scale_y,
        baseline_in_card_mm=baseline,
        source_bounds=(x_min, y_min, x_max, y_max),
        advance_units_range=(min(advances), max(advances)),
        max_visible_width_units=max_visible_width,
    )


def glyph_placement(
    character: str,
    face: FontFace,
    card_x: float,
    card_y: float,
    geometry: SheetGeometry,
    typography: TypographyLayout,
) -> GlyphPlacement:
    glyph_set = face.glyph_set()
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

    scale_x = typography.scale_x
    scale_y = typography.scale_y
    visible_width_mm = (x_max - x_min) * scale_x
    x_mm = card_x + (geometry.card_width_mm - visible_width_mm) / 2 - x_min * scale_x
    baseline_y_mm = card_y + typography.baseline_in_card_mm

    visible_left = x_mm + x_min * scale_x
    visible_right = x_mm + x_max * scale_x
    visible_top = baseline_y_mm - y_max * scale_y
    visible_bottom = baseline_y_mm - y_min * scale_y
    tolerance = 1e-6
    if not (
        card_x + geometry.glyph_padding_x_mm - tolerance <= visible_left
        and visible_right
        <= card_x + geometry.card_width_mm - geometry.glyph_padding_x_mm + tolerance
        and card_y + geometry.glyph_padding_y_mm - tolerance <= visible_top
        and visible_bottom
        <= card_y
        + geometry.artwork_height_mm
        - geometry.glyph_padding_y_mm
        + tolerance
    ):
        raise StickerError(f"glyph {character!r} exceeds its safe card limits")

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
    x = geometry.margin_mm + column * (geometry.card_width_mm + geometry.column_gap_mm)
    y = geometry.margin_mm + row * (
        geometry.artwork_height_mm + geometry.row_gap_mm
    )
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
    characters = [
        character
        for character in profile.characters
        if not (omit_blank and character == " ")
    ]
    page_width, page_height, _ = geometry.page_size(len(characters))
    face = faces[0]
    typography = typography_layout(profile.characters, face, geometry)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{number(page_width)}mm" '
            f'height="{number(page_height)}mm" viewBox="0 0 {number(page_width)} '
            f'{number(page_height)}">'
        ),
        f"  <title>{xml_escape(profile.name)} sticker sheet</title>",
        "  <defs>",
    ]
    for sheet_index in range(len(characters)):
        x, y, _, _ = card_origin(sheet_index, geometry)
        lines.append(
            f'    <clipPath id="clip-card-{sheet_index + 1:02d}" '
            f'clipPathUnits="userSpaceOnUse"><rect x="{number(x)}" y="{number(y)}" '
            f'width="{number(geometry.card_width_mm)}" '
            f'height="{number(geometry.artwork_height_mm)}"/></clipPath>'
        )
    lines.extend(
        [
            "  </defs>",
            '  <g id="backgrounds">',
        ]
    )
    positions: list[dict[str, Any]] = []
    placements: list[GlyphPlacement | None] = []

    for sheet_index, character in enumerate(characters):
        x, y, row, column = card_origin(sheet_index, geometry)
        lines.append(
            f'    <rect id="card-{sheet_index + 1:02d}" x="{number(x)}" y="{number(y)}" '
            f'width="{number(geometry.card_width_mm)}" height="{number(geometry.artwork_height_mm)}" '
            f'fill="{background}"/>'
        )
        placement = None
        font_label = None
        if character != " ":
            placement = glyph_placement(character, face, x, y, geometry, typography)
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
    lines.append(f'  <g id="glyphs" fill="{foreground}" fill-rule="nonzero">')
    for sheet_index, placement in enumerate(placements):
        if placement is None:
            continue
        lines.append(f'    <g clip-path="url(#clip-card-{sheet_index + 1:02d})">')
        lines.append(
            f'      <path id="glyph-{sheet_index + 1:02d}" data-character="{xml_escape(placement.character)}" '
            f'd="{placement.path_data}" transform="translate({number(placement.x_mm)} '
            f"{number(placement.baseline_y_mm)}) scale({number(placement.scale_x)} "
            f'-{number(placement.scale_y)})"/>'
        )
        lines.append("    </g>")
    lines.append("  </g>")

    if include_guides:
        lines.append(
            f'  <g id="cut-guides" fill="none" stroke="{guide_color}" '
            f'stroke-width="{number(geometry.guide_width_mm)}">'
        )
        for sheet_index in range(len(characters)):
            x, y, _, _ = card_origin(sheet_index, geometry)
            lower_y = y + geometry.split_y_mm + geometry.cut_gap_mm
            lower_height = geometry.card_height_mm - geometry.split_y_mm
            lines.append(
                f'    <rect x="{number(x)}" y="{number(y)}" width="{number(geometry.card_width_mm)}" '
                f'height="{number(geometry.split_y_mm)}"/>'
            )
            lines.append(
                f'    <rect x="{number(x)}" y="{number(lower_y)}" width="{number(geometry.card_width_mm)}" '
                f'height="{number(lower_height)}"/>'
            )
        lines.append("  </g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n", positions


def build_cut_svg(
    profile: CharacterSet,
    geometry: SheetGeometry,
    guide_color: str,
    omit_blank: bool,
) -> str:
    """Build a cutter-only SVG so guides never cover the printed artwork."""

    characters = [
        character
        for character in profile.characters
        if not (omit_blank and character == " ")
    ]
    page_width, page_height, _ = geometry.page_size(len(characters))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{number(page_width)}mm" '
            f'height="{number(page_height)}mm" viewBox="0 0 {number(page_width)} '
            f'{number(page_height)}">'
        ),
        f"  <title>{xml_escape(profile.name)} cut paths</title>",
        f'  <g id="cut-guides" fill="none" stroke="{guide_color}" '
        f'stroke-width="{number(geometry.guide_width_mm)}">',
    ]
    for sheet_index in range(len(characters)):
        x, y, _, _ = card_origin(sheet_index, geometry)
        lower_y = y + geometry.split_y_mm + geometry.cut_gap_mm
        lower_height = geometry.card_height_mm - geometry.split_y_mm
        lines.append(
            f'    <rect x="{number(x)}" y="{number(y)}" '
            f'width="{number(geometry.card_width_mm)}" '
            f'height="{number(geometry.split_y_mm)}"/>'
        )
        lines.append(
            f'    <rect x="{number(x)}" y="{number(lower_y)}" '
            f'width="{number(geometry.card_width_mm)}" '
            f'height="{number(lower_height)}"/>'
        )
    lines.extend(["  </g>", "</svg>"])
    return "\n".join(lines) + "\n"


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
            coordinate for point in (point1, point2, point3) for coordinate in point
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
    characters = [
        character
        for character in profile.characters
        if not (omit_blank and character == " ")
    ]
    page_width, page_height, _ = geometry.page_size(len(characters))
    face = faces[0]
    typography = typography_layout(profile.characters, face, geometry)
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(
        str(output),
        pagesize=(page_width * mm, page_height * mm),
        pageCompression=1,
        invariant=1,
    )
    pdf.setTitle(f"{profile.name} sticker sheet")
    pdf.setAuthor("Alphabets sticker generator")
    pdf.setSubject(DEFAULT_LICENSE_TEXT)

    pdf.setFillColor(HexColor(background))
    for index in range(len(characters)):
        x, y_top, _, _ = card_origin(index, geometry)
        y = page_height - y_top - geometry.artwork_height_mm
        pdf.rect(
            x * mm,
            y * mm,
            geometry.card_width_mm * mm,
            geometry.artwork_height_mm * mm,
            fill=1,
            stroke=0,
        )

    pdf.setFillColor(HexColor(foreground))
    for index, character in enumerate(characters):
        if character == " ":
            continue
        x, y_top, _, _ = card_origin(index, geometry)
        placement = glyph_placement(character, face, x, y_top, geometry, typography)
        glyph_set = face.glyph_set()
        pdf_path = pdf.beginPath()
        glyph_set[placement.glyph_name].draw(CanvasPathPen(glyph_set, pdf_path))
        pdf.saveState()
        clip_path = pdf.beginPath()
        clip_y = page_height - y_top - geometry.artwork_height_mm
        clip_path.rect(
            x * mm,
            clip_y * mm,
            geometry.card_width_mm * mm,
            geometry.artwork_height_mm * mm,
        )
        pdf.clipPath(clip_path, stroke=0, fill=0)
        pdf.translate(placement.x_mm * mm, (page_height - placement.baseline_y_mm) * mm)
        pdf.scale(placement.scale_x * mm, placement.scale_y * mm)
        # OpenType contours use non-zero winding. ReportLab defaults to the
        # even-odd rule, which punches false inverse rectangles where contours
        # overlap (most visibly across the crossbar of A and accented A glyphs).
        pdf.drawPath(pdf_path, fill=1, stroke=0, fillMode=1)
        pdf.restoreState()

    if include_guides:
        pdf.setStrokeColor(HexColor(guide_color))
        pdf.setLineWidth(geometry.guide_width_mm * mm)
        for index in range(len(characters)):
            x, y_top, _, _ = card_origin(index, geometry)
            upper_y = page_height - y_top - geometry.split_y_mm
            pdf.rect(
                x * mm,
                upper_y * mm,
                geometry.card_width_mm * mm,
                geometry.split_y_mm * mm,
                fill=0,
                stroke=1,
            )
            lower_height = geometry.card_height_mm - geometry.split_y_mm
            lower_y = (
                page_height
                - y_top
                - geometry.split_y_mm
                - geometry.cut_gap_mm
                - lower_height
            )
            pdf.rect(
                x * mm,
                lower_y * mm,
                geometry.card_width_mm * mm,
                lower_height * mm,
                fill=0,
                stroke=1,
            )

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
    physical_variant: PhysicalVariant | None = None,
) -> dict[str, Any]:
    page_width, page_height, rows = geometry.page_size(len(positions))
    typography = typography_layout(profile.characters, faces[0], geometry)
    return {
        "schema_version": 1,
        "generator": "generate_stickers.py",
        "character_set": {
            "id": profile.id,
            "name": profile.name,
            "characters": profile.characters,
        },
        "physical_variant": physical_variant.id if physical_variant else None,
        "colors": {
            "preset": color_preset,
            "background": background,
            "foreground": foreground,
            "guide": guide_color if include_guides else None,
        },
        "geometry_mm": {
            "card": [geometry.card_width_mm, geometry.card_height_mm],
            "cut_half": [geometry.card_width_mm, geometry.split_y_mm],
            "cut_gap": geometry.cut_gap_mm,
            "artwork": [geometry.card_width_mm, geometry.artwork_height_mm],
            "page": [page_width, page_height],
            "margin": geometry.margin_mm,
            "column_gap": geometry.column_gap_mm,
            "row_gap": geometry.row_gap_mm,
            "split_y": geometry.split_y_mm,
            "glyph_padding": [
                geometry.glyph_padding_x_mm,
                geometry.glyph_padding_y_mm,
            ],
            "columns": geometry.columns,
            "rows": rows,
        },
        "omit_blank": omit_blank,
        "typography": {
            "alignment": "common-transform-baseline-centered-bounds",
            "spacing": "monospaced" if typography.is_monospaced else "proportional",
            "scale_x_mm_per_font_unit": typography.scale_x,
            "scale_y_mm_per_font_unit": typography.scale_y,
            "width_ratio": typography.width_ratio,
            "advance_range_mm": list(typography.advance_mm_range),
            "max_visible_width_mm": typography.max_visible_width_units
            * typography.scale_x,
            "baseline_from_card_top_mm": typography.baseline_in_card_mm,
            "vertical_padding_min_mm": geometry.glyph_padding_y_mm,
        },
        "fonts": [
            {
                "role": "sheet",
                "file": face.path.name,
                "family": face.family,
                "style": face.style,
                "variation": face.variation_location,
                "sha256": face.sha256,
            }
            for face in faces
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
    source.add_argument(
        "--variant",
        choices=("prototype", "definitive"),
        help="matched V2 physical variant: character preset and sticker geometry",
    )
    source.add_argument(
        "--preset", help="character preset id (default: catalog default)"
    )
    source.add_argument(
        "--settings", type=Path, help="settings JSON with preset or custom characters"
    )
    parser.add_argument(
        "--color-preset", choices=sorted(COLOR_PRESETS), default=DEFAULT_COLOR_PRESET
    )
    parser.add_argument("--background", help="background override in #RRGGBB notation")
    parser.add_argument(
        "--foreground", help="letter-color override in #RRGGBB notation"
    )
    parser.add_argument(
        "--guide-color", default="#FF00FF", help="cut-guide color in #RRGGBB notation"
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=DEFAULT_FONT,
        help="single OpenType font; it must contain every selected character",
    )
    parser.add_argument(
        "--font-weight",
        type=float,
        default=DEFAULT_FONT_WEIGHT,
        help="optional wght axis value for a variable font",
    )
    parser.add_argument(
        "--font-width",
        type=float,
        default=DEFAULT_FONT_WIDTH,
        help="optional wdth axis value for a variable font",
    )
    parser.add_argument("--columns", type=int, default=22)
    parser.add_argument("--card-width", type=float, default=55.0)
    parser.add_argument("--card-height", type=float, default=86.0)
    parser.add_argument("--horizontal-padding", type=float, default=0.0)
    parser.add_argument("--vertical-padding", type=float, default=0.0)
    parser.add_argument(
        "--cut-gap",
        type=float,
        default=0.0,
        help="uncut printed gap between the two sticker rectangles",
    )
    parser.add_argument(
        "--omit-blank", action="store_true", help="omit the blank drum position"
    )
    guide_mode = parser.add_mutually_exclusive_group()
    guide_mode.add_argument(
        "--guides",
        dest="include_guides",
        action="store_true",
        help="overlay cut guides on print artwork (default)",
    )
    guide_mode.add_argument(
        "--no-guides",
        dest="include_guides",
        action="store_false",
        help="omit cut outlines and center lines from print artwork",
    )
    parser.set_defaults(include_guides=True)
    parser.add_argument("--output-svg", type=Path, required=True)
    parser.add_argument("--output-pdf", type=Path)
    parser.add_argument(
        "--output-cut-svg",
        type=Path,
        help="write separate cutter-only SVG with card outlines and center cuts",
    )
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args(argv)


def option_was_supplied(argv: Sequence[str] | None, option: str) -> bool:
    """Tell explicit dimension overrides apart from argparse defaults."""

    arguments = tuple(sys.argv[1:] if argv is None else argv)
    return any(
        argument == option or argument.startswith(f"{option}=")
        for argument in arguments
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        physical_variant = load_variant(args.variant) if args.variant else None
        if physical_variant:
            if (
                option_was_supplied(argv, "--card-width")
                and args.card_width != physical_variant.sticker.width_mm
            ):
                raise StickerError(
                    f"{physical_variant.name} requires a {physical_variant.sticker.width_mm:g} mm sticker width"
                )
            if (
                option_was_supplied(argv, "--card-height")
                and args.card_height != physical_variant.sticker.height_mm
            ):
                raise StickerError(
                    f"{physical_variant.name} requires a {physical_variant.sticker.height_mm:g} mm sticker height"
                )
            if (
                option_was_supplied(argv, "--cut-gap")
                and args.cut_gap != physical_variant.sticker.cut_gap_mm
            ):
                raise StickerError(
                    f"{physical_variant.name} requires a {physical_variant.sticker.cut_gap_mm:g} mm cut gap"
                )
            profile = load_profile(physical_variant.character_preset, None)
            card_width = physical_variant.sticker.width_mm
            card_height = physical_variant.sticker.height_mm
            split_y = physical_variant.sticker.split_y_mm
            cut_gap = physical_variant.sticker.cut_gap_mm
        else:
            profile = load_profile(args.preset, args.settings)
            card_width = args.card_width
            card_height = args.card_height
            split_y = card_height / 2
            cut_gap = args.cut_gap
        background, foreground = resolve_colors(
            args.color_preset, args.background, args.foreground
        )
        guide_color = normalize_color(args.guide_color)
        faces = [FontFace.load(args.font, args.font_weight, args.font_width)]
        for character in profile.characters:
            if character != " ":
                select_face(character, faces)
        geometry = SheetGeometry(
            card_width_mm=card_width,
            card_height_mm=card_height,
            columns=args.columns,
            glyph_padding_x_mm=args.horizontal_padding,
            glyph_padding_y_mm=args.vertical_padding,
            split_y_mm=split_y,
            cut_gap_mm=cut_gap,
        )
        include_guides = args.include_guides
        svg, positions = build_svg(
            profile,
            faces,
            geometry,
            background,
            foreground,
            guide_color,
            include_guides,
            args.omit_blank,
        )
        args.output_svg.parent.mkdir(parents=True, exist_ok=True)
        args.output_svg.write_text(svg, encoding="utf-8")
        embed_artifact_license(args.output_svg)
        if args.output_cut_svg:
            args.output_cut_svg.parent.mkdir(parents=True, exist_ok=True)
            args.output_cut_svg.write_text(
                build_cut_svg(profile, geometry, guide_color, args.omit_blank),
                encoding="utf-8",
            )
            embed_artifact_license(args.output_cut_svg)
        if args.output_pdf:
            write_pdf(
                args.output_pdf,
                profile,
                faces,
                geometry,
                background,
                foreground,
                guide_color,
                include_guides,
                args.omit_blank,
            )
        manifest_path = args.manifest or args.output_svg.with_suffix(".json")
        manifest = build_manifest(
            profile,
            faces,
            positions,
            geometry,
            args.color_preset,
            background,
            foreground,
            guide_color,
            include_guides,
            args.omit_blank,
            physical_variant,
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        write_licensed_json(manifest_path, manifest)
    except (
        StickerError,
        CharacterSetError,
        PhysicalVariantError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
