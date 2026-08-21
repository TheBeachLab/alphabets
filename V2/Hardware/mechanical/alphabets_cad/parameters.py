"""Manufacturing dimensions shared by every CadQuery part.

All dimensions are millimetres. Values reproduce the current V2 card,
OpenSCAD drum, 28BYJ-48 reference model, and dormant holder-side profile.
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
    body_width: float = 50.0
    total_height: float = 48.0
    tab_width: float = 4.0
    tab_height: float = 2.5
    thickness: float = 1.0

    @property
    def body_height(self) -> float:
        return self.total_height - self.tab_height

    @property
    def overall_width(self) -> float:
        return self.body_width + 2 * self.tab_width

    @property
    def tab_axis_height(self) -> float:
        """Height of the flap's hinge axis, centred through the tab strip."""

        return self.body_height + self.tab_height / 2

    @property
    def tab_rotation_radius(self) -> float:
        """Corner radius of the tab's height-by-thickness pivot section."""

        return math.hypot(self.tab_height / 2, self.thickness / 2)


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
    flap_hole_center_radius: float = 40.0
    motor_axis_width: float = 3.0
    motor_axis_height: float = 6.0
    motor_axis_radius: float = 2.5
    shaft_axis_radius: float = 1.5

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
    """Printable two-part enclosure around the current 85 mm drum."""

    wall_thickness: float = 2.4
    front_thickness: float = 3.0
    radial_clearance: float = 2.0
    axial_clearance: float = 2.0
    window_clearance: float = 1.0
    window_corner_radius: float = 2.0
    outer_corner_radius: float = 4.0
    split_gap: float = 0.2
    motor_bore_diameter: float = 10.0
    shaft_bore_diameter: float = 3.4
    motor_mount_hole_diameter: float = 4.4
    rear_lug_radius: float = 3.8
    rear_lug_height: float = 6.0
    rear_lug_edge_overlap: float = 1.9
    rear_lug_inset: float = 8.0
    screw_clearance_diameter: float = 3.4
    screw_pilot_diameter: float = 2.6
    screw_head_diameter: float = 6.2
    screw_head_depth: float = 2.0


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
        return self.drum_outer_width + 2 * self.drum_enclosure.axial_clearance

    @property
    def enclosure_outer_width(self) -> float:
        return self.enclosure_inner_width + 2 * self.drum_enclosure.wall_thickness

    @property
    def enclosure_inner_height(self) -> float:
        return self.drum.diameter + 2 * self.drum_enclosure.radial_clearance

    @property
    def enclosure_outer_height(self) -> float:
        return self.enclosure_inner_height + 2 * self.drum_enclosure.wall_thickness

    @property
    def enclosure_inner_depth(self) -> float:
        return self.drum.diameter + 2 * self.drum_enclosure.radial_clearance

    @property
    def enclosure_outer_depth(self) -> float:
        return self.enclosure_inner_depth + self.drum_enclosure.front_thickness

    @property
    def enclosure_window_width(self) -> float:
        return self.card.body_width + 2 * self.drum_enclosure.window_clearance

    @property
    def enclosure_window_height(self) -> float:
        return self.card.total_height + 2 * self.drum_enclosure.window_clearance

    @property
    def flap_tab_radial_clearance(self) -> float:
        """Actual radial gap between a tab corner and its circular pivot hole."""

        return self.drum.flap_hole_diameter / 2 - self.card.tab_rotation_radius

    @property
    def enclosure_rear_lug_center_x(self) -> float:
        enclosure = self.drum_enclosure
        return (
            self.enclosure_outer_width / 2
            + enclosure.rear_lug_radius
            - enclosure.rear_lug_edge_overlap
        )

    @property
    def enclosure_overall_width(self) -> float:
        enclosure = self.drum_enclosure
        return 2 * (self.enclosure_rear_lug_center_x + enclosure.rear_lug_radius)

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["card"]["body_height"] = self.card.body_height
        result["card"]["overall_width"] = self.card.overall_width
        result["card"]["tab_axis_height"] = self.card.tab_axis_height
        result["card"]["tab_rotation_radius"] = self.card.tab_rotation_radius
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
                "inner_depth": self.enclosure_inner_depth,
                "outer_depth": self.enclosure_outer_depth,
                "window_width": self.enclosure_window_width,
                "window_height": self.enclosure_window_height,
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
    if result.flap_tab_radial_clearance < result.drum.flap_rotation_clearance:
        raise ValueError(
            "card tab does not have the required radial clearance to rotate "
            "inside the drum flap hole"
        )
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
