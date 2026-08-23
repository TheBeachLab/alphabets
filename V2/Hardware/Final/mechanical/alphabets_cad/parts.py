# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""CadQuery solids reconstructed from the current mechanical sources."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cadquery as cq

from .parameters import DESIGN, DesignParameters

EPSILON = 0.05
ALPHA_FONT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "stickers/fonts/OverpassMono-Medium.otf"
)


@dataclass(frozen=True)
class CapturedEnclosureLimits:
    """Asymmetric enclosure planes derived from one settled Blender capture."""

    inner_x_min: float
    inner_x_max: float
    back_y: float
    front_y: float
    inner_bottom_z: float
    inner_top_z: float
    outer_x_min: float
    outer_x_max: float
    outer_bottom_z: float
    outer_top_z: float

    @property
    def outer_width(self) -> float:
        return self.outer_x_max - self.outer_x_min

    @property
    def outer_depth(self) -> float:
        return self.front_y - self.back_y

    @property
    def outer_height(self) -> float:
        return self.outer_top_z - self.outer_bottom_z


def _cutting_cylinder(radius: float, height: float) -> cq.Workplane:
    return (
        cq.Workplane("XY", origin=(0, 0, -EPSILON))
        .circle(radius)
        .extrude(height + 2 * EPSILON)
    )


def _cutting_box(length: float, width: float, height: float) -> cq.Workplane:
    return cq.Workplane("XY", origin=(0, 0, -EPSILON)).box(
        length,
        width,
        height + 2 * EPSILON,
        centered=(True, True, False),
    )


def card_points(
    params: DesignParameters = DESIGN,
) -> tuple[tuple[float, float], ...]:
    card = params.card
    return (
        (0.0, 0.0),
        (card.body_width, 0.0),
        (card.body_width, card.tab_start_height),
        (card.body_width + card.tab_width, card.tab_start_height),
        (card.body_width + card.tab_width, card.total_height),
        (-card.tab_width, card.total_height),
        (-card.tab_width, card.tab_start_height),
        (0.0, card.tab_start_height),
    )


def flap_card(params: DesignParameters = DESIGN) -> cq.Shape:
    """Bare split-flap card, including its unstickered drum tabs."""

    return (
        cq.Workplane("XY")
        .polyline(card_points(params))
        .close()
        .extrude(params.card.thickness)
        .val()
        .clean()
    )


def flap_sticker_layers(
    params: DesignParameters = DESIGN,
) -> dict[str, cq.Shape]:
    """Separate front and back sticker solids in the card's local coordinates."""

    card = params.card
    sticker = (
        cq.Workplane("XY")
        .box(
            card.sticker_width,
            card.sticker_face_height,
            card.sticker_face_thickness,
            centered=(False, False, False),
        )
        .translate((card.sticker_side_margin, card.sticker_y_offset, 0))
        .val()
    )
    return {
        "front": sticker.translate((0, 0, -card.sticker_face_thickness)),
        "back": sticker.translate((0, 0, card.thickness)),
    }


def finished_flap_card(params: DesignParameters = DESIGN) -> cq.Shape:
    """Card with a centered sticker on each visible face, leaving bare margins."""

    blank = flap_card(params)
    stickers = flap_sticker_layers(params)
    return blank.fuse(stickers["front"]).fuse(stickers["back"]).clean()


def _flap_hole_centers(
    params: DesignParameters = DESIGN,
) -> tuple[tuple[float, float], ...]:
    drum = params.drum
    return tuple(
        (
            drum.flap_hole_center_radius
            * math.cos(2 * math.pi * index / drum.positions),
            drum.flap_hole_center_radius
            * math.sin(2 * math.pi * index / drum.positions),
        )
        for index in range(drum.positions)
    )


def _motor_axis_cut(
    params: DesignParameters = DESIGN, height: float | None = None
) -> cq.Workplane:
    drum = params.drum
    cut_height = height if height is not None else drum.side_thickness
    rectangle = _cutting_box(
        drum.motor_axis_width - drum.laser_kerf,
        drum.motor_axis_height,
        cut_height,
    )
    circle = _cutting_cylinder(drum.motor_axis_radius, cut_height)
    return rectangle.intersect(circle)


def laser_cut_disc(
    motor_side: bool,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """One acrylic drum side with 64 flap holes, axis and support slots."""

    drum = params.drum
    result = cq.Workplane("XY").circle(drum.radius).extrude(drum.side_thickness)
    flap_holes = (
        cq.Workplane("XY", origin=(0, 0, -EPSILON))
        .pushPoints(_flap_hole_centers(params))
        .circle(drum.flap_hole_diameter / 2)
        .extrude(drum.side_thickness + 2 * EPSILON)
    )
    result = result.cut(flap_holes)
    if motor_side:
        result = result.cut(_motor_axis_cut(params))
    else:
        result = result.cut(
            _cutting_cylinder(drum.shaft_axis_radius, drum.side_thickness)
        )

    slot_width = drum.support_tab_width - 2 * drum.laser_kerf
    slot_height = drum.side_thickness - 2 * drum.laser_kerf
    slot_x = drum.support_width / 2 - drum.support_tab_width / 2
    slots = _cutting_box(slot_width, slot_height, drum.side_thickness)
    for x in (-slot_x, slot_x):
        for y in (-drum.support_y, drum.support_y):
            result = result.cut(slots.translate((x, y, 0)))
    return result.val().clean()


def drum_support(params: DesignParameters = DESIGN) -> cq.Shape:
    """One laser-cut internal support with tabs for both drum sides."""

    drum = params.drum
    result = cq.Workplane("XY").box(
        drum.support_width,
        params.drum_inner_width,
        drum.side_thickness,
        centered=(True, True, False),
    )
    tab_x = drum.support_width / 2 - drum.support_tab_width / 2
    tab_y = params.drum_inner_width / 2 + drum.side_thickness / 2
    tab = cq.Workplane("XY").box(
        drum.support_tab_width,
        drum.side_thickness,
        drum.side_thickness,
        centered=(True, True, False),
    )
    for x in (-tab_x, tab_x):
        for y in (-tab_y, tab_y):
            result = result.union(tab.translate((x, y, 0)))
    return result.val().clean()


def _printed_ring(params: DesignParameters = DESIGN) -> cq.Workplane:
    drum = params.drum
    printed = params.printed_spool
    result = (
        cq.Workplane("XY")
        .circle(drum.radius)
        .circle(drum.radius - printed.ring_width)
        .extrude(printed.thickness)
    )
    holes = (
        cq.Workplane("XY", origin=(0, 0, -EPSILON))
        .pushPoints(_flap_hole_centers(params))
        .circle(drum.flap_hole_diameter / 2)
        .extrude(printed.thickness + 2 * EPSILON)
    )
    return result.cut(holes)


def _printed_disc_base(params: DesignParameters = DESIGN) -> cq.Workplane:
    drum = params.drum
    printed = params.printed_spool
    ring = _printed_ring(params)
    translated_rings = (
        _printed_ring(params)
        .translate((drum.radius, 0, 0))
        .union(_printed_ring(params).translate((-drum.radius, 0, 0)))
    )
    hub = (
        cq.Workplane("XY").circle(printed.center_hub_radius).extrude(printed.thickness)
    )
    inner_limit = (
        cq.Workplane("XY")
        .circle(drum.radius - printed.ring_width)
        .extrude(printed.thickness)
    )
    web = translated_rings.union(hub).intersect(inner_limit)
    return ring.union(web)


def printed_spool_disc(
    motor_side: bool,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Legacy lightweight 3D-printed drum side."""

    printed = params.printed_spool
    result = _printed_disc_base(params)
    if motor_side:
        result = result.cut(_motor_axis_cut(params, height=printed.thickness))
    else:
        pin = (
            cq.Workplane("XY")
            .circle(printed.shaft_pin_radius)
            .extrude(printed.shaft_pin_height)
        )
        result = result.union(pin)
    return result.val().clean()


def motor_components(
    params: DesignParameters = DESIGN,
) -> dict[str, cq.Shape]:
    """28BYJ-48 reference geometry in the coordinate system of the SCAD model."""

    motor = params.motor
    chassis = (
        cq.Workplane("XY", origin=(0, -motor.shaft_offset, -motor.chassis_height))
        .circle(motor.chassis_radius)
        .extrude(motor.chassis_height)
    )
    bracket = cq.Workplane(
        "XY", origin=(0, -motor.shaft_offset, -motor.mount_bracket_height)
    ).box(
        2 * motor.mount_center_offset,
        2 * motor.mount_outer_radius,
        motor.mount_bracket_height,
        centered=(True, True, False),
    )
    mount_end = (
        cq.Workplane("XY", origin=(0, 0, -motor.mount_bracket_height))
        .circle(motor.mount_outer_radius)
        .extrude(motor.mount_bracket_height)
    )
    bracket = bracket.union(
        mount_end.translate((-motor.mount_center_offset, -motor.shaft_offset, 0))
    ).union(mount_end.translate((motor.mount_center_offset, -motor.shaft_offset, 0)))
    mount_holes = (
        cq.Workplane("XY", origin=(0, 0, -motor.mount_bracket_height - EPSILON))
        .pushPoints(
            (
                (-motor.mount_center_offset, -motor.shaft_offset),
                (motor.mount_center_offset, -motor.shaft_offset),
            )
        )
        .circle(motor.mount_hole_radius)
        .extrude(motor.mount_bracket_height + 2 * EPSILON)
    )
    body = chassis.union(bracket.cut(mount_holes))
    collar = (
        cq.Workplane("XY")
        .circle(motor.shaft_collar_radius)
        .extrude(motor.shaft_collar_height)
    )
    backpack = cq.Workplane(
        "XY",
        origin=(
            0,
            -motor.shaft_offset - motor.backpack_extent / 2,
            -motor.backpack_height,
        ),
    ).box(
        motor.backpack_width,
        motor.backpack_extent,
        motor.backpack_height,
        centered=(True, True, False),
    )
    round_shaft_height = motor.shaft_height - motor.shaft_flat_height
    shaft_round = (
        cq.Workplane("XY").circle(motor.shaft_radius).extrude(round_shaft_height)
    )
    shaft_flat = (
        cq.Workplane("XY", origin=(0, 0, round_shaft_height))
        .circle(motor.shaft_radius)
        .extrude(motor.shaft_flat_height)
        .intersect(
            cq.Workplane("XY", origin=(0, 0, round_shaft_height))
            .rect(2 * motor.shaft_radius, motor.shaft_flat_width)
            .extrude(motor.shaft_flat_height)
        )
    )
    return {
        "motor_body": body.val().clean(),
        "motor_collar": collar.val().clean(),
        "motor_backpack": backpack.val().clean(),
        "motor_shaft": shaft_round.union(shaft_flat).val().clean(),
    }


def motor_reference(params: DesignParameters = DESIGN) -> cq.Shape:
    components = tuple(motor_components(params).values())
    return cq.Compound.makeCompound(list(components))


def legacy_holder_side(params: DesignParameters = DESIGN) -> cq.Shape:
    """Dormant `side()` profile from the legacy spool-holder OpenSCAD file."""

    holder = params.holder
    base = cq.Workplane("XY").circle(holder.end_radius).extrude(holder.thickness)
    arm = cq.Workplane("XY", origin=(holder.length / 2, 0, 0)).box(
        holder.length,
        holder.width,
        holder.thickness,
        centered=(True, True, False),
    )
    end_tab = cq.Workplane(
        "XY",
        origin=(
            holder.length + holder.thickness / 2,
            -holder.width / 2 + holder.end_tab_length / 2,
            0,
        ),
    ).box(
        holder.thickness,
        holder.end_tab_length,
        holder.thickness,
        centered=(True, True, False),
    )
    second_tab = end_tab.translate((0, holder.width - holder.end_tab_length, 0))
    axis = _cutting_cylinder(holder.axis_radius, holder.thickness)
    return base.union(arm).union(end_tab).union(second_tab).cut(axis).val().clean()


def legacy_holder_inset(params: DesignParameters = DESIGN) -> cq.Shape:
    holder = params.holder
    return (
        cq.Workplane("XY")
        .box(
            holder.thickness,
            holder.end_tab_length,
            holder.thickness,
            centered=(False, False, False),
        )
        .val()
    )


def enclosure_reference_edges(
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """The exact non-solid sketch preserved in `side_motor.FCStd`."""

    enclosure = params.enclosure_reference
    x0 = -enclosure.left_width
    x1 = enclosure.right_width
    y0 = -enclosure.lower_height
    y1 = enclosure.upper_height
    outer = cq.Wire.makePolygon(
        [
            cq.Vector(x0, y0, 0),
            cq.Vector(x1, y0, 0),
            cq.Vector(x1, y1, 0),
            cq.Vector(x0, y1, 0),
            cq.Vector(x0, y0, 0),
        ]
    )
    vertical = cq.Edge.makeLine(cq.Vector(0, y0, 0), cq.Vector(0, y1, 0))
    horizontal = cq.Edge.makeLine(cq.Vector(x0, 0, 0), cq.Vector(x1, 0, 0))
    upper_reference = cq.Edge.makeLine(
        cq.Vector(x0, enclosure.upper_reference_start, 0),
        cq.Vector(
            x0,
            enclosure.upper_reference_start + enclosure.reference_line_length,
            0,
        ),
    )
    lower_reference = cq.Edge.makeLine(
        cq.Vector(x0, enclosure.lower_reference_start, 0),
        cq.Vector(
            x0,
            enclosure.lower_reference_start - enclosure.reference_line_length,
            0,
        ),
    )
    return cq.Compound.makeCompound(
        [outer, vertical, horizontal, upper_reference, lower_reference]
    )


def _x_axis_cylinder(
    radius: float,
    length: float,
    x: float,
    y: float,
    z: float,
) -> cq.Solid:
    return cq.Solid.makeCylinder(
        radius,
        length,
        cq.Vector(x, y, z),
        cq.Vector(1, 0, 0),
    )


def _rounded_rectangle_wire(
    plane: cq.Plane,
    width: float,
    height: float,
    radius: float,
) -> cq.Wire:
    """Rounded rectangle wire located on an arbitrary side-face plane."""

    wire = (
        cq.Workplane("XY")
        .rect(width, height)
        .extrude(EPSILON)
        .edges("|Z")
        .fillet(radius)
        .faces("<Z")
        .wires()
        .val()
    )
    return wire.moved(plane.location)


def _motor_electronics_pocket_bounds(
    params: DesignParameters,
) -> tuple[float, float, float, float]:
    """Inner rounded-rectangle bounds covering the motor and 50 x 35 mm PCB."""

    enclosure = params.drum_enclosure
    motor = params.motor
    clearance = enclosure.docking_clearance
    half_card_width = enclosure.electronics_card_width / 2
    card_clearance = (
        enclosure.electronics_card_clearance
        + enclosure.motor_electronics_corner_radius * (1 - 1 / math.sqrt(2))
    )
    minimum_y = min(
        enclosure.electronics_card_center_y - half_card_width - card_clearance,
        -motor.mount_center_offset - motor.mount_outer_radius - clearance,
    )
    maximum_y = max(
        enclosure.electronics_card_center_y + half_card_width + card_clearance,
        motor.mount_center_offset + motor.mount_outer_radius + clearance,
    )
    minimum_z = min(
        enclosure.electronics_card_center_z
        - enclosure.electronics_card_height / 2
        - card_clearance,
        -motor.shaft_offset
        - motor.backpack_extent
        - clearance
        - enclosure.motor_cable_clearance,
    )
    maximum_z = max(
        enclosure.electronics_card_center_z
        + enclosure.electronics_card_height / 2
        + card_clearance,
        -motor.shaft_offset + motor.chassis_radius + clearance,
    )
    return minimum_y, maximum_y, minimum_z, maximum_z


def _x_axis_chamfered_circle(
    radius: float,
    depth: float,
    chamfer: float,
    x: float,
    y: float,
    z: float,
    direction: int,
) -> cq.Shape:
    """Circle recess with a 45-degree lead-in from an exterior side face."""

    transition = min(chamfer, depth)
    outer_plane = cq.Plane(
        origin=(x, y, z),
        xDir=(0, 1, 0),
        normal=(direction, 0, 0),
    )
    inner_x = x + direction * transition
    inner_plane = cq.Plane(
        origin=(inner_x, y, z),
        xDir=(0, 1, 0),
        normal=(direction, 0, 0),
    )
    lead_in = cq.Solid.makeLoft(
        [
            cq.Workplane(outer_plane).circle(radius + transition).val(),
            cq.Workplane(inner_plane).circle(radius).val(),
        ],
        True,
    )
    if transition == depth:
        return lead_in.clean()
    straight = cq.Solid.makeCylinder(
        radius,
        depth - transition + EPSILON,
        cq.Vector(inner_x, y, z),
        cq.Vector(direction, 0, 0),
    )
    return lead_in.fuse(straight).clean()


def _x_axis_chamfered_rectangle(
    width: float,
    height: float,
    depth: float,
    chamfer: float,
    x: float,
    y: float,
    z: float,
    direction: int,
) -> cq.Shape:
    """Rectangular recess with a 45-degree lead-in from a side face."""

    transition = min(chamfer, depth)
    outer_plane = cq.Plane(
        origin=(x, y, z),
        xDir=(0, 1, 0),
        normal=(direction, 0, 0),
    )
    inner_x = x + direction * transition
    inner_plane = cq.Plane(
        origin=(inner_x, y, z),
        xDir=(0, 1, 0),
        normal=(direction, 0, 0),
    )
    lead_in = cq.Solid.makeLoft(
        [
            cq.Workplane(outer_plane)
            .rect(width + 2 * transition, height + 2 * transition)
            .val(),
            cq.Workplane(inner_plane).rect(width, height).val(),
        ],
        True,
    )
    if transition == depth:
        return lead_in.clean()
    straight = (
        cq.Workplane(inner_plane)
        .rect(width, height)
        .extrude(depth - transition + EPSILON)
        .val()
    )
    return lead_in.fuse(straight).clean()


def captured_enclosure_limits(
    capture: Mapping[str, Any],
    params: DesignParameters = DESIGN,
) -> CapturedEnclosureLimits:
    """Derive compact enclosure planes from cards, floor and fixed pawl.

    The floor is authoritative for the lower internal plane. Card vertices that
    have penetrated slightly below it in Bullet are therefore ignored instead
    of making the enclosure taller.
    """

    enclosure = params.drum_enclosure
    cards = capture["all_cards_bounds_world_mm"]
    floor = capture["floor"]["bounds_world_mm"]
    pawl = capture["pawl"]["bounds_world_mm"]

    card_minimum = tuple(float(value) for value in cards["minimum"])
    card_maximum = tuple(float(value) for value in cards["maximum"])
    pawl_minimum = tuple(float(value) for value in pawl["minimum"])
    pawl_maximum = tuple(float(value) for value in pawl["maximum"])
    floor_top = float(floor["maximum"][2])
    floor_front = float(floor["maximum"][1])

    half_drum_width = params.drum_outer_width / 2
    inner_x_min = min(card_minimum[0], -half_drum_width) - enclosure.axial_clearance
    inner_x_max = max(card_maximum[0], half_drum_width) + enclosure.axial_clearance
    back_y = (
        min(card_minimum[1], -params.drum.radius) - enclosure.capture_card_clearance
    )
    front_y = min(floor_front, pawl_minimum[1])
    inner_top_z = (
        max(card_maximum[2], pawl_maximum[2], params.drum.radius)
        + enclosure.capture_top_clearance
    )

    return CapturedEnclosureLimits(
        inner_x_min=inner_x_min,
        inner_x_max=inner_x_max,
        back_y=back_y,
        front_y=front_y,
        inner_bottom_z=floor_top,
        inner_top_z=inner_top_z,
        outer_x_min=inner_x_min - enclosure.capture_wall_thickness,
        outer_x_max=inner_x_max + enclosure.capture_wall_thickness,
        outer_bottom_z=floor_top - enclosure.floor_thickness,
        outer_top_z=inner_top_z + enclosure.capture_wall_thickness,
    )


def _captured_motor_mount_pocket(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Convex motor/PCB pocket with one continuous printable side lead-in."""

    enclosure = params.drum_enclosure
    start_x = limits.outer_x_min - EPSILON
    depth = enclosure.motor_inset_depth + EPSILON
    chamfer = min(enclosure.side_feature_chamfer, enclosure.motor_inset_depth)
    minimum_y, maximum_y, minimum_z, maximum_z = _motor_electronics_pocket_bounds(
        params
    )
    center_y = (minimum_y + maximum_y) / 2
    center_z = (minimum_z + maximum_z) / 2
    width = maximum_y - minimum_y
    height = maximum_z - minimum_z
    outer_plane = cq.Plane(
        origin=(start_x, center_y, center_z),
        xDir=(0, 1, 0),
        normal=(1, 0, 0),
    )
    inner_x = start_x + chamfer
    inner_plane = cq.Plane(
        origin=(inner_x, center_y, center_z),
        xDir=(0, 1, 0),
        normal=(1, 0, 0),
    )
    outer_wire = _rounded_rectangle_wire(
        outer_plane,
        width + 2 * chamfer,
        height + 2 * chamfer,
        enclosure.motor_electronics_corner_radius + chamfer,
    )
    inner_wire = _rounded_rectangle_wire(
        inner_plane,
        width,
        height,
        enclosure.motor_electronics_corner_radius,
    )
    lead_in = cq.Solid.makeLoft([outer_wire, inner_wire], True)
    if chamfer == depth:
        return lead_in.clean()
    straight = cq.Solid.extrudeLinear(
        inner_wire,
        [],
        cq.Vector(depth - chamfer + EPSILON, 0, 0),
    )
    return lead_in.fuse(straight).clean()


def _captured_electronics_card_envelope(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Exact 50 x 35 mm PCB envelope spanning the six-millimetre side pocket."""

    enclosure = params.drum_enclosure
    return (
        cq.Workplane("XY")
        .box(
            enclosure.motor_inset_depth,
            enclosure.electronics_card_width,
            enclosure.electronics_card_height,
        )
        .translate(
            (
                limits.outer_x_min + enclosure.motor_inset_depth / 2,
                enclosure.electronics_card_center_y,
                enclosure.electronics_card_center_z,
            )
        )
        .val()
    )


def _captured_motor_mount_bosses(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Two internal bosses carrying the motor's M3 self-tapping pilots."""

    enclosure = params.drum_enclosure
    anchor_x = limits.outer_x_min + enclosure.motor_inset_depth
    inner_wall_x = limits.inner_x_min
    boss_end_x = -params.drum_outer_width / 2 - enclosure.motor_mount_disc_clearance
    embedded_length = inner_wall_x - anchor_x
    visible_length = boss_end_x - inner_wall_x
    radial_taper = min(
        enclosure.boss_end_chamfer,
        enclosure.motor_mount_boss_radius - enclosure.screw_pilot_diameter / 2,
    )
    bosses = []
    for mount_y in (
        -params.motor.mount_center_offset,
        params.motor.mount_center_offset,
    ):
        straight = cq.Solid.makeCylinder(
            enclosure.motor_mount_boss_radius,
            embedded_length,
            cq.Vector(anchor_x, mount_y, -params.motor.shaft_offset),
            cq.Vector(1, 0, 0),
        )
        lead_out = cq.Solid.makeCone(
            enclosure.motor_mount_boss_radius,
            enclosure.motor_mount_boss_radius - radial_taper,
            visible_length,
            cq.Vector(
                inner_wall_x,
                mount_y,
                -params.motor.shaft_offset,
            ),
            cq.Vector(1, 0, 0),
        )
        bosses.append(straight.fuse(lead_out).clean())
    return bosses[0].fuse(bosses[1]).clean()


def _captured_motor_mount_pilots(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """M3 pilots from the recessed motor face through both internal bosses."""

    enclosure = params.drum_enclosure
    start_x = limits.outer_x_min + enclosure.motor_inset_depth - EPSILON
    end_x = -params.drum_outer_width / 2 - enclosure.motor_mount_disc_clearance
    pilots = [
        cq.Solid.makeCylinder(
            enclosure.screw_pilot_diameter / 2,
            end_x - start_x + EPSILON,
            cq.Vector(start_x, mount_y, -params.motor.shaft_offset),
            cq.Vector(1, 0, 0),
        )
        for mount_y in (
            -params.motor.mount_center_offset,
            params.motor.mount_center_offset,
        )
    ]
    return cq.Compound.makeCompound(pilots)


def _captured_docking_recess(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Opposite recess matching the motor inset with a printable lead-in."""

    enclosure = params.drum_enclosure
    motor = params.motor
    return _x_axis_chamfered_circle(
        motor.chassis_radius + enclosure.docking_clearance,
        enclosure.docking_recess_depth + EPSILON,
        min(enclosure.side_feature_chamfer, enclosure.docking_recess_depth),
        limits.outer_x_max + EPSILON,
        0,
        -motor.shaft_offset,
        -1,
    )


def _captured_shaft_support(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Lower-half boss with an M3 self-tapping pilot for a screw axle."""

    enclosure = params.drum_enclosure
    anchor_x = limits.outer_x_max - enclosure.docking_recess_depth + EPSILON
    inner_wall_x = limits.inner_x_max
    disc_outer_x = params.drum_outer_width / 2
    boss_end_x = disc_outer_x + enclosure.shaft_support_axial_clearance

    embedded_length = anchor_x - inner_wall_x
    visible_length = inner_wall_x - boss_end_x
    radial_taper = min(
        enclosure.boss_end_chamfer,
        enclosure.shaft_support_boss_radius - enclosure.screw_pilot_diameter / 2,
    )
    boss = cq.Solid.makeCylinder(
        enclosure.shaft_support_boss_radius,
        embedded_length,
        cq.Vector(anchor_x, 0, 0),
        cq.Vector(-1, 0, 0),
    )
    boss = boss.fuse(
        cq.Solid.makeCone(
            enclosure.shaft_support_boss_radius,
            enclosure.shaft_support_boss_radius - radial_taper,
            visible_length,
            cq.Vector(inner_wall_x, 0, 0),
            cq.Vector(-1, 0, 0),
        )
    )
    pilot = cq.Solid.makeCylinder(
        enclosure.screw_pilot_diameter / 2,
        anchor_x - boss_end_x + EPSILON,
        cq.Vector(anchor_x + EPSILON, 0, 0),
        cq.Vector(-1, 0, 0),
    )
    return boss.cut(pilot).clean()


def _captured_shaft_head_recess(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Flat Ø6 mm counterbore for the screw axle head on the shaft side."""

    enclosure = params.drum_enclosure
    start_x = limits.outer_x_max - enclosure.docking_recess_depth + EPSILON
    return cq.Solid.makeCylinder(
        enclosure.shaft_head_recess_diameter / 2,
        enclosure.shaft_head_recess_depth + 2 * EPSILON,
        cq.Vector(start_x, 0, 0),
        cq.Vector(-1, 0, 0),
    )


def _captured_alignment_centers(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> tuple[tuple[float, float], ...]:
    enclosure = params.drum_enclosure
    x_centers = (
        (limits.outer_x_min + limits.inner_x_min) / 2,
        (limits.outer_x_max + limits.inner_x_max) / 2,
    )
    y_centers = (
        limits.back_y + enclosure.alignment_end_inset,
        limits.front_y - enclosure.alignment_end_inset,
    )
    return tuple((x, y) for x in x_centers for y in y_centers)


def _captured_alignment_frustums(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
    *,
    sockets: bool,
) -> cq.Shape:
    """Four 45-degree truncated pyramids or their clearance sockets."""

    enclosure = params.drum_enclosure
    split_height = enclosure.capture_split_height
    lower_split = split_height - enclosure.split_gap / 2
    upper_split = split_height + enclosure.split_gap / 2
    clearance = enclosure.alignment_clearance if sockets else 0.0
    base_size = enclosure.alignment_base_size + 2 * clearance
    top_size = enclosure.alignment_top_size + 2 * clearance
    start_z = upper_split - EPSILON if sockets else lower_split - EPSILON
    height = enclosure.alignment_height + 2 * EPSILON
    frustums = []
    for x, y in _captured_alignment_centers(limits, params):
        frustums.append(
            cq.Workplane("XY", origin=(x, y, start_z))
            .rect(base_size, base_size)
            .workplane(offset=height)
            .rect(top_size, top_size)
            .loft(combine=True)
            .val()
        )
    return cq.Compound.makeCompound(frustums)


def _captured_stack_alignment_centers(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> tuple[tuple[float, float], ...]:
    """Four distributed top/bottom docking locations."""

    enclosure = params.drum_enclosure
    x_centers = (
        limits.outer_x_min + enclosure.stack_alignment_x_inset,
        limits.outer_x_max - enclosure.stack_alignment_x_inset,
    )
    y_centers = (
        limits.back_y + enclosure.stack_alignment_y_inset,
        limits.front_y - enclosure.stack_alignment_y_inset,
    )
    return tuple((x, y) for x in x_centers for y in y_centers)


def _captured_stack_alignment_frustums(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
    *,
    sockets: bool,
) -> cq.Shape:
    """Downward male keys or matching upper sockets for vertical stacking."""

    enclosure = params.drum_enclosure
    clearance = enclosure.alignment_clearance if sockets else 0.0
    base_size = enclosure.alignment_base_size + 2 * clearance
    tip_size = enclosure.alignment_top_size + 2 * clearance
    height = enclosure.alignment_height
    if sockets:
        start_z = limits.outer_top_z - height - EPSILON
        end_z = limits.outer_top_z + EPSILON
    else:
        start_z = limits.outer_bottom_z - height
        end_z = limits.outer_bottom_z + EPSILON

    frustums = []
    for x, y in _captured_stack_alignment_centers(limits, params):
        frustums.append(
            cq.Workplane("XY", origin=(x, y, start_z))
            .rect(tip_size, tip_size)
            .workplane(offset=end_z - start_z)
            .rect(base_size, base_size)
            .loft(combine=True)
            .val()
        )
    return cq.Compound.makeCompound(frustums)


def _captured_magnet_pockets(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
    *,
    upper: bool,
) -> cq.Shape:
    """One FDM-compensated magnet insert per side at the centre of the split."""

    enclosure = params.drum_enclosure
    radius = enclosure.magnet_diameter / 2 + enclosure.magnet_radial_clearance
    depth = enclosure.magnet_thickness + enclosure.magnet_depth_clearance + EPSILON
    center_y = (limits.back_y + limits.front_y) / 2
    x_centers = (
        (limits.outer_x_min + limits.inner_x_min) / 2,
        (limits.outer_x_max + limits.inner_x_max) / 2,
    )
    if upper:
        start_z = enclosure.capture_split_height + enclosure.split_gap / 2 - EPSILON
        direction = cq.Vector(0, 0, 1)
    else:
        start_z = enclosure.capture_split_height - enclosure.split_gap / 2 + EPSILON
        direction = cq.Vector(0, 0, -1)
    pockets = [
        cq.Solid.makeCylinder(
            radius,
            depth,
            cq.Vector(x, center_y, start_z),
            direction,
        )
        for x in x_centers
    ]
    return cq.Compound.makeCompound(pockets)


def _captured_stack_magnet_pocket(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
    *,
    top: bool,
) -> cq.Shape:
    """Matching top/bottom magnet pocket centred on the split alpha mark."""

    enclosure = params.drum_enclosure
    radius = enclosure.magnet_diameter / 2 + enclosure.magnet_radial_clearance
    depth = enclosure.magnet_thickness + enclosure.magnet_depth_clearance + EPSILON
    center_y = (limits.back_y + limits.front_y) / 2
    if top:
        start_z = limits.outer_top_z + EPSILON
        direction = cq.Vector(0, 0, -1)
    else:
        start_z = limits.outer_bottom_z - EPSILON
        direction = cq.Vector(0, 0, 1)
    return cq.Solid.makeCylinder(
        radius,
        depth,
        cq.Vector(0, center_y, start_z),
        direction,
    )


def _captured_top_alpha_cutter(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Large split alpha recessed into the top through a nominal 45-degree lead-in."""

    enclosure = params.drum_enclosure
    center_y = (limits.back_y + limits.front_y) / 2
    bottom_z = 0.0
    top_z = enclosure.top_mark_depth + EPSILON

    def split_profiles(size: float, z: float, gap: float) -> list[cq.Solid]:
        text = (
            cq.Workplane("XY", origin=(0, 0, z))
            .text(
                enclosure.top_mark_character,
                size,
                EPSILON,
                combine=False,
                fontPath=str(ALPHA_FONT_PATH),
                halign="center",
                valign="center",
            )
            .val()
            .clean()
        )
        front = (
            cq.Workplane("XY").box(200, 200, 10).translate((0, 100 + gap / 2, z)).val()
        )
        back = (
            cq.Workplane("XY").box(200, 200, 10).translate((0, -100 - gap / 2, z)).val()
        )
        return sorted(
            text.intersect(front.fuse(back)).clean().Solids(),
            key=lambda solid: solid.Center().y,
        )

    # The opening is nominally one millimetre wider around the glyph contour
    # than the pocket floor. The split itself remains a straight 2 mm band.
    bottom = split_profiles(
        enclosure.top_mark_font_size,
        bottom_z,
        enclosure.top_mark_split_gap,
    )
    top = split_profiles(
        enclosure.top_mark_font_size + 4 * enclosure.top_mark_chamfer,
        top_z,
        enclosure.top_mark_split_gap,
    )
    halves = []
    for bottom_half, top_half in zip(bottom, top, strict=True):
        bottom_face = min(
            (
                face
                for face in bottom_half.Faces()
                if abs(abs(face.normalAt().z) - 1) < 1e-6
            ),
            key=lambda face: face.Center().z,
        )
        top_face = min(
            (
                face
                for face in top_half.Faces()
                if abs(abs(face.normalAt().z) - 1) < 1e-6
            ),
            key=lambda face: abs(face.Center().z - top_z),
        )
        halves.append(
            cq.Solid.makeLoft(
                [bottom_face.outerWire(), top_face.outerWire()],
                True,
            )
        )
    mark = cq.Compound.makeCompound(halves).rotate(
        (0, 0, 0),
        (0, 0, 1),
        enclosure.top_mark_rotation,
    )
    return mark.translate(
        (
            0,
            center_y,
            limits.outer_top_z - enclosure.top_mark_depth,
        )
    )


def _captured_pawl_screw_axis_z(limits: CapturedEnclosureLimits) -> float:
    return (limits.inner_top_z + limits.outer_top_z) / 2


def _captured_pawl_pilot(
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """M3 self-tapping pilot entering the front edge of the upper wall."""

    enclosure = params.drum_enclosure
    return cq.Solid.makeCylinder(
        enclosure.screw_pilot_diameter / 2,
        enclosure.pawl_pilot_depth + EPSILON,
        cq.Vector(0, limits.front_y + EPSILON, _captured_pawl_screw_axis_z(limits)),
        cq.Vector(0, -1, 0),
    )


def _captured_pawl_shape(
    capture: Mapping[str, Any],
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
    *,
    tip_extension: float = 0.0,
) -> cq.Shape:
    """Replaceable rounded pawl with a flush front pad and M3 clearance hole."""

    enclosure = params.drum_enclosure
    bounds = capture["pawl"]["bounds_world_mm"]
    minimum = tuple(float(value) for value in bounds["minimum"])
    maximum = tuple(float(value) for value in bounds["maximum"])
    center_x = (minimum[0] + maximum[0]) / 2
    blade_half_width = enclosure.pawl_mount_width / 2
    tip_z = minimum[2] - tip_extension
    base_z = limits.inner_top_z
    thickness = maximum[1] - minimum[1] + enclosure.pawl_thickness_addition
    tip_radius = min(enclosure.pawl_tip_radius, blade_half_width / 2)
    tip_center_z = tip_z + tip_radius
    mount_height = limits.outer_top_z - limits.inner_top_z
    mount_center_z = _captured_pawl_screw_axis_z(limits)

    blade = (
        cq.Workplane("XZ", origin=(0, limits.front_y, 0))
        .polyline(
            (
                (center_x - blade_half_width, base_z),
                (center_x + blade_half_width, base_z),
                (center_x + tip_radius, tip_center_z),
                (center_x - tip_radius, tip_center_z),
            )
        )
        .close()
        .extrude(-thickness)
        .val()
    )
    rounded_tip = (
        cq.Workplane("XZ", origin=(0, limits.front_y, 0))
        .center(center_x, tip_center_z)
        .circle(tip_radius)
        .extrude(-thickness)
        .val()
    )
    mount_pad = (
        cq.Workplane("XZ", origin=(0, limits.front_y, 0))
        .center(center_x, mount_center_z)
        .rect(enclosure.pawl_mount_width, mount_height)
        .extrude(-thickness)
        .val()
    )
    outer = mount_pad.fuse(blade).fuse(rounded_tip).clean()
    outer = (
        cq.Workplane(obj=outer)
        .faces(">Y")
        .edges()
        .chamfer(enclosure.pawl_outer_chamfer)
        .val()
        .clean()
    )
    screw_clearance = cq.Solid.makeCylinder(
        enclosure.screw_clearance_diameter / 2,
        thickness + 2 * EPSILON,
        cq.Vector(center_x, limits.front_y - EPSILON, mount_center_z),
        cq.Vector(0, 1, 0),
    )
    head_recess = cq.Solid.makeCylinder(
        enclosure.pawl_head_recess_diameter / 2,
        enclosure.pawl_head_recess_depth + EPSILON,
        cq.Vector(
            center_x,
            limits.front_y + thickness + EPSILON,
            mount_center_z,
        ),
        cq.Vector(0, -1, 0),
    )
    return outer.cut(screw_clearance).cut(head_recess).clean()


def _captured_pawl_mount(
    capture: Mapping[str, Any],
    limits: CapturedEnclosureLimits,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Definitive-card replaceable pawl retained as the default viewer part."""

    return _captured_pawl_shape(capture, limits, params)


def captured_pawl_parts(
    capture: Mapping[str, Any],
    params: DesignParameters = DESIGN,
) -> dict[str, cq.Shape]:
    """Interchangeable pawls for the 48 mm definitive and 43 mm prototype cards."""

    limits = captured_enclosure_limits(capture, params)
    return {
        "pawl_definitive": _captured_pawl_shape(capture, limits, params),
        "pawl_prototype": _captured_pawl_shape(
            capture,
            limits,
            params,
            tip_extension=params.drum_enclosure.prototype_pawl_extension,
        ),
    }


def _captured_enclosure_shell(
    capture: Mapping[str, Any],
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Open-ended hollow tube fitted to the settled cards and saved floor."""

    enclosure = params.drum_enclosure
    limits = captured_enclosure_limits(capture, params)
    outer = (
        cq.Workplane("XY")
        .box(limits.outer_width, limits.outer_depth, limits.outer_height)
        .translate(
            (
                (limits.outer_x_min + limits.outer_x_max) / 2,
                (limits.back_y + limits.front_y) / 2,
                (limits.outer_bottom_z + limits.outer_top_z) / 2,
            )
        )
        .edges("|Y")
        .fillet(enclosure.capture_outer_corner_radius)
    )
    inner_corner_radius = max(
        enclosure.capture_outer_corner_radius - enclosure.capture_wall_thickness,
        0.5,
    )
    cavity = (
        cq.Workplane("XY")
        .box(
            limits.inner_x_max - limits.inner_x_min,
            limits.outer_depth + 2 * EPSILON,
            limits.inner_top_z - limits.inner_bottom_z,
        )
        .translate(
            (
                (limits.inner_x_min + limits.inner_x_max) / 2,
                (limits.back_y + limits.front_y) / 2,
                (limits.inner_bottom_z + limits.inner_top_z) / 2,
            )
        )
        .edges("|Y")
        .fillet(inner_corner_radius)
    )
    shell = outer.cut(cavity).val()

    front_inner_selector = cq.selectors.BoxSelector(
        (
            limits.inner_x_min - EPSILON,
            limits.front_y - EPSILON / 2,
            limits.inner_bottom_z - EPSILON,
        ),
        (
            limits.inner_x_max + EPSILON,
            limits.front_y + EPSILON / 2,
            limits.inner_top_z + EPSILON,
        ),
    )
    shell = (
        cq.Workplane(obj=shell)
        .edges(front_inner_selector)
        .chamfer(enclosure.front_inner_chamfer)
        .val()
    )
    pawl_land_width = enclosure.pawl_mount_width + 2 * enclosure.pawl_mount_land_margin
    pawl_mount_land = (
        cq.Workplane("XY")
        .box(
            pawl_land_width,
            enclosure.front_inner_chamfer,
            limits.outer_top_z - limits.inner_top_z,
        )
        .translate(
            (
                0,
                limits.front_y - enclosure.front_inner_chamfer / 2,
                (limits.inner_top_z + limits.outer_top_z) / 2,
            )
        )
        .val()
    )
    shell = shell.fuse(pawl_mount_land).clean()

    shell = shell.cut(_captured_motor_mount_pocket(limits, params)).cut(
        _captured_docking_recess(limits, params)
    )
    shell = shell.fuse(_captured_motor_mount_bosses(limits, params)).clean()
    shell = shell.cut(_captured_motor_mount_pilots(limits, params))

    motor_bore_wall = enclosure.capture_wall_thickness - enclosure.motor_inset_depth
    shell = shell.cut(
        _x_axis_chamfered_circle(
            enclosure.motor_bore_diameter / 2,
            motor_bore_wall + 2 * EPSILON,
            motor_bore_wall,
            limits.outer_x_min + enclosure.motor_inset_depth - EPSILON,
            0,
            0,
            1,
        )
    )
    return shell.cut(_captured_pawl_pilot(limits, params)).clean()


def _captured_enclosure_half(
    upper: bool,
    capture: Mapping[str, Any],
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    enclosure = params.drum_enclosure
    limits = captured_enclosure_limits(capture, params)
    lower_split = enclosure.capture_split_height - enclosure.split_gap / 2
    upper_split = enclosure.capture_split_height + enclosure.split_gap / 2
    if upper:
        clip_min = upper_split
        clip_max = limits.outer_top_z + 1
    else:
        clip_min = limits.outer_bottom_z - 1
        clip_max = lower_split

    clipping_box = (
        cq.Workplane("XY")
        .box(
            limits.outer_width + 20,
            2 * limits.outer_depth,
            clip_max - clip_min,
        )
        .translate(
            (
                (limits.outer_x_min + limits.outer_x_max) / 2,
                (limits.back_y + limits.front_y) / 2,
                (clip_min + clip_max) / 2,
            )
        )
        .val()
    )
    half = _captured_enclosure_shell(capture, params).intersect(clipping_box).clean()
    alignment = _captured_alignment_frustums(
        limits,
        params,
        sockets=upper,
    )
    stack_alignment = _captured_stack_alignment_frustums(
        limits,
        params,
        sockets=upper,
    )
    if upper:
        half = (
            half.cut(alignment)
            .cut(stack_alignment)
            .cut(_captured_top_alpha_cutter(limits, params))
            .cut(_captured_magnet_pockets(limits, params, upper=True))
            .cut(_captured_stack_magnet_pocket(limits, params, top=True))
            .clean()
        )
    else:
        half = (
            half.fuse(_captured_shaft_support(limits, params))
            .fuse(alignment)
            .fuse(stack_alignment)
            .cut(_captured_shaft_head_recess(limits, params))
            .cut(_captured_magnet_pockets(limits, params, upper=False))
            .cut(_captured_stack_magnet_pocket(limits, params, top=False))
            .clean()
        )
    return half


def captured_drum_enclosure_parts(
    capture: Mapping[str, Any],
    params: DesignParameters = DESIGN,
) -> dict[str, cq.Shape]:
    """Two printable enclosure halves fitted to a captured settled mechanism."""

    return {
        "enclosure_upper": _captured_enclosure_half(True, capture, params),
        "enclosure_lower": _captured_enclosure_half(False, capture, params),
    }
