"""Validated physical profiles for the two incompatible V2 hardware sets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

V2_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_PATH = V2_DIR / "variants" / "variants.json"


class PhysicalVariantError(ValueError):
    """Raised when a physical V2 variant contract is invalid."""


@dataclass(frozen=True)
class StickerDimensions:
    width_mm: float
    height_mm: float
    split_y_mm: float

    @property
    def face_height_mm(self) -> float:
        return self.split_y_mm


@dataclass(frozen=True)
class CardDimensions:
    body_width_mm: float
    visible_height_mm: float
    total_height_mm: float
    tab_width_mm: float
    tab_height_mm: float
    material_thickness_mm: float
    sticker_face_thickness_mm: float

    @property
    def finished_thickness_mm(self) -> float:
        return self.material_thickness_mm + 2 * self.sticker_face_thickness_mm

    def sticker_side_margin_mm(self, sticker: StickerDimensions) -> float:
        return (self.body_width_mm - sticker.width_mm) / 2


@dataclass(frozen=True)
class DrumDimensions:
    positions: int
    diameter_mm: float
    inner_width_mm: float
    side_thickness_mm: float
    outer_width_mm: float


@dataclass(frozen=True)
class EnclosureSource:
    status: str
    source: str
    note: str


@dataclass(frozen=True)
class PhysicalVariant:
    id: str
    name: str
    description: str
    character_preset: str
    sticker: StickerDimensions
    card: CardDimensions
    drum: DrumDimensions
    enclosure: EnclosureSource
    artifacts: dict[str, Any]


def _number(data: dict[str, Any], key: str, context: str) -> float:
    value = data.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise PhysicalVariantError(f"{context}.{key} must be a positive number")
    return float(value)


def _text(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise PhysicalVariantError(f"{context}.{key} must be a non-empty string")
    return value


def _variant(data: dict[str, Any]) -> PhysicalVariant:
    variant_id = _text(data, "id", "variant")
    sticker_data = data.get("sticker_mm")
    card_data = data.get("card_mm")
    drum_data = data.get("drum_mm")
    enclosure_data = data.get("enclosure")
    artifacts = data.get("artifacts")
    if not all(
        isinstance(item, dict)
        for item in (sticker_data, card_data, drum_data, enclosure_data, artifacts)
    ):
        raise PhysicalVariantError(
            f"variant {variant_id!r} has an invalid physical section"
        )

    sticker = StickerDimensions(
        _number(sticker_data, "width", f"{variant_id}.sticker_mm"),
        _number(sticker_data, "height", f"{variant_id}.sticker_mm"),
        _number(sticker_data, "split_y", f"{variant_id}.sticker_mm"),
    )
    card = CardDimensions(
        _number(card_data, "body_width", f"{variant_id}.card_mm"),
        _number(card_data, "visible_height", f"{variant_id}.card_mm"),
        _number(card_data, "total_height", f"{variant_id}.card_mm"),
        _number(card_data, "tab_width", f"{variant_id}.card_mm"),
        _number(card_data, "tab_height", f"{variant_id}.card_mm"),
        _number(card_data, "material_thickness", f"{variant_id}.card_mm"),
        _number(card_data, "sticker_face_thickness", f"{variant_id}.card_mm"),
    )
    positions = drum_data.get("positions")
    if not isinstance(positions, int) or positions <= 0:
        raise PhysicalVariantError(
            f"{variant_id}.drum_mm.positions must be a positive integer"
        )
    drum = DrumDimensions(
        positions,
        _number(drum_data, "diameter", f"{variant_id}.drum_mm"),
        _number(drum_data, "inner_width", f"{variant_id}.drum_mm"),
        _number(drum_data, "side_thickness", f"{variant_id}.drum_mm"),
        _number(drum_data, "outer_width", f"{variant_id}.drum_mm"),
    )
    enclosure = EnclosureSource(
        _text(enclosure_data, "status", f"{variant_id}.enclosure"),
        _text(enclosure_data, "source", f"{variant_id}.enclosure"),
        _text(enclosure_data, "note", f"{variant_id}.enclosure"),
    )
    if enclosure.status not in {"legacy-reference", "manufacturing-source"}:
        raise PhysicalVariantError(
            f"variant {variant_id!r} has unknown enclosure status"
        )
    return PhysicalVariant(
        id=variant_id,
        name=_text(data, "name", "variant"),
        description=_text(data, "description", "variant"),
        character_preset=_text(data, "character_preset", "variant"),
        sticker=sticker,
        card=card,
        drum=drum,
        enclosure=enclosure,
        artifacts=artifacts,
    )


def _validate_match(variant: PhysicalVariant) -> None:
    if variant.drum.positions != 64:
        raise PhysicalVariantError(
            f"variant {variant.id!r} must retain 64 drum positions"
        )
    if variant.sticker.width_mm >= variant.card.body_width_mm:
        raise PhysicalVariantError(
            f"variant {variant.id!r} sticker must leave a lateral placement margin"
        )
    if variant.sticker.height_mm != 2 * variant.card.visible_height_mm:
        raise PhysicalVariantError(
            f"variant {variant.id!r} sticker does not contain two visible faces"
        )
    if variant.sticker.split_y_mm != variant.card.visible_height_mm:
        raise PhysicalVariantError(
            f"variant {variant.id!r} split does not match visible card height"
        )
    if (
        variant.card.visible_height_mm + variant.card.tab_height_mm
        != variant.card.total_height_mm
    ):
        raise PhysicalVariantError(
            f"variant {variant.id!r} card height does not match tab band"
        )
    expected_inner = variant.card.body_width_mm + 1.0
    if variant.drum.inner_width_mm != expected_inner:
        raise PhysicalVariantError(
            f"variant {variant.id!r} drum inner width must include 1 mm clearance"
        )
    expected_outer = variant.drum.inner_width_mm + 2 * variant.drum.side_thickness_mm
    if round(variant.drum.outer_width_mm, 6) != round(expected_outer, 6):
        raise PhysicalVariantError(
            f"variant {variant.id!r} drum outer width is inconsistent"
        )


def load_variants(path: Path | None = None) -> dict[str, PhysicalVariant]:
    catalog_path = path or DEFAULT_CATALOG_PATH
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PhysicalVariantError(
            f"cannot read physical variant catalog: {catalog_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise PhysicalVariantError(
            f"invalid physical variant catalog: {catalog_path}"
        ) from error
    if data.get("schema_version") != 1:
        raise PhysicalVariantError("unsupported physical variant catalog schema")
    entries = data.get("variants")
    if not isinstance(entries, list) or not entries:
        raise PhysicalVariantError("physical variant catalog has no variants")
    variants: dict[str, PhysicalVariant] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise PhysicalVariantError("physical variant entry must be an object")
        variant = _variant(entry)
        if variant.id in variants:
            raise PhysicalVariantError(f"duplicate physical variant id: {variant.id!r}")
        _validate_match(variant)
        variants[variant.id] = variant
    default_variant = data.get("default_variant")
    if default_variant not in variants:
        raise PhysicalVariantError("physical variant default does not exist")
    return variants


def load_variant(variant_id: str, path: Path | None = None) -> PhysicalVariant:
    variants = load_variants(path)
    try:
        return variants[variant_id]
    except KeyError as error:
        raise PhysicalVariantError(
            f"unknown physical V2 variant: {variant_id!r}"
        ) from error
