"""Manufacturing dimensions shared by every CadQuery part.

All dimensions are millimetres. Values reproduce the current V2 card,
OpenSCAD drum, 28BYJ-48 reference model, and dormant holder-side profile.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CardDimensions:
    body_width: float = 50.0
    total_height: float = 48.0
    tab_width: float = 4.0
    tab_height: float = 3.0
    thickness: float = 1.0

    @property
    def body_height(self) -> float:
        return self.total_height - self.tab_height

    @property
    def overall_width(self) -> float:
        return self.body_width + 2 * self.tab_width


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

    @property
    def drum_inner_width(self) -> float:
        return self.card.body_width + self.drum.axial_clearance

    @property
    def drum_outer_width(self) -> float:
        return self.drum_inner_width + 2 * self.drum.side_thickness

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["card"]["body_height"] = self.card.body_height
        result["card"]["overall_width"] = self.card.overall_width
        result["drum"]["inner_width"] = self.drum_inner_width
        result["drum"]["outer_width"] = self.drum_outer_width
        return result


DESIGN = DesignParameters()
