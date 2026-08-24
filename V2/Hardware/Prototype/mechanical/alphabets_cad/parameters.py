# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Manufacturing dimensions shared by every Prototype CadQuery part.

All dimensions are millimetres. The active card and drum values come from the
matched Prototype variant contract; the motor and dormant holder remain copied
reference geometry.
"""

from __future__ import annotations

import math
import tomllib
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CardDimensions:
    body_width: float = 55.0
    total_height: float = 43.0
    tab_width: float = 4.0
    tab_height: float = 3.0
    thickness: float = 0.5
    sticker_width: float = 50.0
    sticker_face_height: float = 40.0
    sticker_face_thickness: float = 0.1

    @property
    def tab_start_height(self) -> float:
        return self.total_height - self.tab_height

    @property
    def overall_width(self) -> float:
        return self.body_width + 2 * self.tab_width

    @property
    def tab_axis_height(self) -> float:
        """Height of the flap's hinge axis, centred through the tab strip."""

        return self.tab_start_height + self.tab_height / 2

    @property
    def tab_rotation_radius(self) -> float:
        """Corner radius of the tab's height-by-thickness pivot section."""

        return math.hypot(self.tab_height / 2, self.thickness / 2)

    @property
    def finished_thickness(self) -> float:
        """Card body thickness with one sticker applied to each face."""

        return self.thickness + 2 * self.sticker_face_thickness

    @property
    def sticker_side_margin(self) -> float:
        """Equal placement margin on each lateral edge of the card body."""

        return (self.body_width - self.sticker_width) / 2

    @property
    def sticker_y_offset(self) -> float:
        """Offset that aligns the sticker's far edge with the hinge edge."""

        return self.total_height - self.sticker_face_height


@dataclass(frozen=True)
class DrumDimensions:
    positions: int = 64
    diameter: float = 85.0
    side_thickness: float = 2.15
    laser_kerf: float = 0.1
    axial_clearance: float = 1.0
    support_width: float = 35.0
    support_tab_width: float = 6.0
    support_y: float = 20.0
    flap_hole_diameter: float = 3.0
    flap_rotation_clearance: float = 0.15
    allow_tab_interference: bool = True
    flap_hole_center_radius: float = 40.0
    motor_axis_width: float = 3.0
    motor_axis_height: float = 6.0
    motor_axis_radius: float = 2.5
    shaft_axis_radius: float = 1.7

    @property
    def radius(self) -> float:
        return self.diameter / 2


@dataclass(frozen=True)
class PrintedSpoolDimensions:
    thickness: float = 2.0
    ring_width: float = 5.0
    center_hub_radius: float = 6.5
    shaft_pin_radius: float = 1.5
    shaft_pin_height: float = 5.0


@dataclass(frozen=True)
class MotorDimensions:
    chassis_radius: float = 14.0
    chassis_height: float = 19.0
    shaft_offset: float = 8.0
    mount_outer_radius: float = 3.5
    mount_hole_radius: float = 2.1
    mount_center_offset: float = 17.5
    mount_bracket_height: float = 0.8
    shaft_collar_radius: float = 4.5
    shaft_collar_height: float = 1.5
    shaft_radius: float = 2.5
    shaft_height: float = 10.0
    shaft_flat_width: float = 3.0
    shaft_flat_height: float = 6.0
    backpack_width: float = 14.6
    backpack_extent: float = 18.0
    backpack_height: float = 16.0


@dataclass(frozen=True)
class HolderDimensions:
    end_radius: float = 20.0
    axis_radius: float = 5.0
    length: float = 80.0
    width: float = 40.0
    end_tab_length: float = 10.0
    thickness: float = 2.5
    kerf: float = 0.2


@dataclass(frozen=True)
class EnclosureReferenceDimensions:
    left_width: float = 40.0
    right_width: float = 60.0
    upper_height: float = 60.0
    lower_height: float = 75.0
    reference_line_length: float = 41.5
    upper_reference_start: float = 1.751
    lower_reference_start: float = -2.11899


@dataclass(frozen=True)
class DrumEnclosureDimensions:
    """Printable one-piece enclosure around the current drum."""

    top_distance: float = 66.32
    bottom_distance: float = 75.0
    back_distance: float = 64.75
    side_clearance: float = 2.0
    wall_thickness: float = 8.0
    side_inset_depth: float = 6.0
    capture_outer_corner_radius: float = 10.0
    pawl_mount_land_margin: float = 2.0
    docking_clearance: float = 0.3
    side_pocket_chamfer: float = 6.0
    side_pocket_margin: float = 6.0
    side_pocket_corner_radius: float = 8.0
    boss_end_chamfer: float = 1.5
    electronics_card_width: float = 50.0
    electronics_card_height: float = 35.0
    electronics_card_center_y: float = 0.0
    electronics_card_center_z: float = -50.0
    motor_bore_diameter: float = 10.0
    shaft_bore_diameter: float = 3.4
    motor_mount_hole_diameter: float = 4.4
    shaft_support_axial_clearance: float = 0.5
    shaft_support_boss_radius: float = 4.5
    shaft_head_recess_diameter: float = 6.0
    shaft_head_recess_depth: float = 2.0
    motor_mount_disc_clearance: float = 0.5
    motor_mount_boss_radius: float = 4.5
    alignment_height: float = 3.0
    alignment_base_size: float = 8.0
    alignment_top_size: float = 2.0
    alignment_clearance: float = 0.2
    stack_alignment_x_inset: float = 14.0
    stack_alignment_y_inset: float = 20.0
    top_mark_character: str = "α"
    top_mark_font_size: float = 90.0
    top_mark_depth: float = 0.2
    top_mark_chamfer: float = 0.2
    top_mark_split_gap: float = 2.0
    top_mark_rotation: float = 180.0
    pawl_mount_width: float = 10.0
    pawl_pilot_depth: float = 8.0
    pawl_thickness_addition: float = 1.0
    pawl_outer_chamfer: float = 1.0
    pawl_head_recess_diameter: float = 6.0
    pawl_head_recess_depth: float = 1.0
    pawl_tip_radius: float = 2.0
    prototype_pawl_extension: float = 3.0
    screw_clearance_diameter: float = 3.4
    screw_pilot_diameter: float = 2.6
    screw_head_diameter: float = 6.2
    screw_head_depth: float = 2.0

    @property
    def front_chamfer(self) -> float:
        """Front inner-edge chamfer derived from the enclosure thickness."""

        return self.wall_thickness / 2

    @property
    def remaining_side_wall(self) -> float:
        """Material left behind both side recesses."""

        return self.wall_thickness - self.side_inset_depth


@dataclass(frozen=True)
class DesignParameters:
    card: CardDimensions = field(default_factory=CardDimensions)
    drum: DrumDimensions = field(default_factory=DrumDimensions)
    printed_spool: PrintedSpoolDimensions = field(
        default_factory=PrintedSpoolDimensions
    )
    motor: MotorDimensions = field(default_factory=MotorDimensions)
    holder: HolderDimensions = field(default_factory=HolderDimensions)
    enclosure_reference: EnclosureReferenceDimensions = field(
        default_factory=EnclosureReferenceDimensions
    )
    drum_enclosure: DrumEnclosureDimensions = field(
        default_factory=DrumEnclosureDimensions
    )

    @property
    def drum_inner_width(self) -> float:
        return self.card.body_width + self.drum.axial_clearance

    @property
    def drum_outer_width(self) -> float:
        return self.drum_inner_width + 2 * self.drum.side_thickness

    @property
    def enclosure_inner_width(self) -> float:
        return self.drum_outer_width + 2 * self.drum_enclosure.side_clearance

    @property
    def enclosure_outer_width(self) -> float:
        return self.enclosure_inner_width + 2 * self.drum_enclosure.wall_thickness

    @property
    def enclosure_inner_height(self) -> float:
        enclosure = self.drum_enclosure
        return enclosure.top_distance + enclosure.bottom_distance

    @property
    def enclosure_ceiling_z(self) -> float:
        return self.drum_enclosure.top_distance

    @property
    def enclosure_floor_z(self) -> float:
        return -self.drum_enclosure.bottom_distance

    @property
    def enclosure_outer_height(self) -> float:
        return self.enclosure_inner_height + 2 * self.drum_enclosure.wall_thickness

    @property
    def flap_tab_radial_clearance(self) -> float:
        """Actual radial gap between a tab corner and its circular pivot hole."""

        return self.drum.flap_hole_diameter / 2 - self.card.tab_rotation_radius

    @property
    def enclosure_overall_width(self) -> float:
        return self.enclosure_outer_width

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["card"]["visible_height"] = self.card.total_height
        result["card"]["tab_start_height"] = self.card.tab_start_height
        result["card"]["overall_width"] = self.card.overall_width
        result["card"]["tab_axis_height"] = self.card.tab_axis_height
        result["card"]["tab_rotation_radius"] = self.card.tab_rotation_radius
        result["card"]["finished_thickness"] = self.card.finished_thickness
        result["card"]["sticker_side_margin"] = self.card.sticker_side_margin
        result["card"]["sticker_y_offset"] = self.card.sticker_y_offset
        result["drum"]["inner_width"] = self.drum_inner_width
        result["drum"]["outer_width"] = self.drum_outer_width
        result["drum"]["flap_tab_radial_clearance"] = self.flap_tab_radial_clearance
        result["drum_enclosure"].update(
            {
                "inner_width": self.enclosure_inner_width,
                "outer_width": self.enclosure_outer_width,
                "overall_width": self.enclosure_overall_width,
                "inner_height": self.enclosure_inner_height,
                "outer_height": self.enclosure_outer_height,
                "ceiling_z": self.enclosure_ceiling_z,
                "floor_z": self.enclosure_floor_z,
                "front_chamfer": self.drum_enclosure.front_chamfer,
                "remaining_side_wall": self.drum_enclosure.remaining_side_wall,
            }
        )
        return result


_SECTIONS = (
    "card",
    "drum",
    "printed_spool",
    "motor",
    "holder",
    "enclosure_reference",
    "drum_enclosure",
)


def design_from_mapping(
    overrides: Mapping[str, Any],
    *,
    base: DesignParameters | None = None,
) -> DesignParameters:
    """Return a design with validated direct-dimension overrides applied.

    Derived dimensions intentionally are not accepted: they remain calculated
    from their physical source dimensions in :class:`DesignParameters`.
    """

    unknown_sections = set(overrides) - set(_SECTIONS)
    if unknown_sections:
        names = ", ".join(sorted(unknown_sections))
        raise ValueError(f"Unknown parameter section(s): {names}")

    design = base or DesignParameters()
    replacements: dict[str, Any] = {}
    for section in _SECTIONS:
        values = overrides.get(section)
        if values is None:
            continue
        if not isinstance(values, Mapping):
            raise TypeError(f"Parameter section {section!r} must be a table")

        current = getattr(design, section)
        valid_fields = {item.name for item in fields(current)}
        unknown_fields = set(values) - valid_fields
        if unknown_fields:
            names = ", ".join(sorted(unknown_fields))
            raise ValueError(f"Unknown parameter(s) in {section}: {names}")
        replacements[section] = replace(current, **values)

    result = replace(design, **replacements)
    if (
        not result.drum.allow_tab_interference
        and result.flap_tab_radial_clearance < result.drum.flap_rotation_clearance
    ):
        raise ValueError(
            "card tab does not have the required radial clearance to rotate "
            "inside the drum flap hole"
        )
    enclosure = result.drum_enclosure
    centre_distances = {
        "top_distance": enclosure.top_distance,
        "bottom_distance": enclosure.bottom_distance,
        "back_distance": enclosure.back_distance,
    }
    for name, value in centre_distances.items():
        if value <= 0:
            raise ValueError(f"{name} must be positive")
    if enclosure.side_clearance < 0:
        raise ValueError("side_clearance cannot be negative")
    if enclosure.wall_thickness <= 0:
        raise ValueError("wall_thickness must be positive")
    if not 0 <= enclosure.side_inset_depth < enclosure.wall_thickness:
        raise ValueError(
            "side_inset_depth must be non-negative and smaller than wall_thickness"
        )
    if enclosure.side_pocket_margin < 0:
        raise ValueError("side_pocket_margin cannot be negative")
    if enclosure.side_pocket_corner_radius < 0:
        raise ValueError("side_pocket_corner_radius cannot be negative")
    side_pocket_chamfer = min(
        enclosure.side_pocket_chamfer,
        enclosure.side_inset_depth,
    )
    if enclosure.side_pocket_corner_radius < side_pocket_chamfer:
        raise ValueError(
            "side_pocket_corner_radius must be at least the side pocket chamfer"
        )
    chamfers = {
        "side_pocket_chamfer": enclosure.side_pocket_chamfer,
        "boss_end_chamfer": enclosure.boss_end_chamfer,
        "top_mark_chamfer": enclosure.top_mark_chamfer,
        "pawl_outer_chamfer": enclosure.pawl_outer_chamfer,
    }
    for name, value in chamfers.items():
        if value < 0:
            raise ValueError(f"{name} cannot be negative")
    return result


def load_design_profile(
    path: Path,
    *,
    base: DesignParameters | None = None,
) -> DesignParameters:
    """Load direct-dimension overrides from a TOML design profile."""

    with path.open("rb") as source:
        profile = tomllib.load(source)
    return design_from_mapping(profile, base=base)


MECHANICAL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = MECHANICAL_DIR / "design.toml"
DESIGN = load_design_profile(DEFAULT_PROFILE)
