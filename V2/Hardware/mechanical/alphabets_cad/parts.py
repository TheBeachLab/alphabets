"""CadQuery solids reconstructed from the current mechanical sources."""

from __future__ import annotations

import math

import cadquery as cq

from .parameters import DESIGN, DesignParameters

EPSILON = 0.05


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


def _drum_enclosure_shell(params: DesignParameters = DESIGN) -> cq.Shape:
    """Shared rounded shell before it is divided at the drum axis."""

    enclosure = params.drum_enclosure
    outer_width = params.enclosure_outer_width
    outer_height = params.enclosure_outer_height
    outer_depth = params.enclosure_outer_depth
    inner_width = params.enclosure_inner_width
    inner_height = params.enclosure_inner_height
    inner_depth = params.enclosure_inner_depth
    front_y = -inner_depth / 2 - enclosure.front_thickness

    outer = (
        cq.Workplane("XY", origin=(0, -enclosure.front_thickness / 2, 0))
        .box(outer_width, outer_depth, outer_height)
        .edges("|Y")
        .fillet(enclosure.outer_corner_radius)
    )
    inner_corner_radius = max(
        enclosure.outer_corner_radius - enclosure.wall_thickness,
        0.5,
    )
    cavity = (
        cq.Workplane("XY", origin=(0, EPSILON, 0))
        .box(inner_width, inner_depth + 2 * EPSILON, inner_height)
        .edges("|Y")
        .fillet(inner_corner_radius)
    )
    window = (
        cq.Workplane(
            "XY",
            origin=(
                0,
                front_y + enclosure.front_thickness / 2,
                0,
            ),
        )
        .box(
            params.enclosure_window_width,
            enclosure.front_thickness + 2 * EPSILON,
            params.enclosure_window_height,
        )
        .edges("|Y")
        .fillet(enclosure.window_corner_radius)
    )
    shell = outer.cut(cavity).cut(window)

    left_outer_x = -outer_width / 2
    right_inner_x = inner_width / 2
    side_cut_length = enclosure.wall_thickness + 2 * EPSILON
    shell = shell.cut(
        _x_axis_cylinder(
            enclosure.motor_bore_diameter / 2,
            side_cut_length,
            left_outer_x - EPSILON,
            0,
            0,
        )
    ).cut(
        _x_axis_cylinder(
            enclosure.shaft_bore_diameter / 2,
            side_cut_length,
            right_inner_x - EPSILON,
            0,
            0,
        )
    )

    for mount_y in (
        -params.motor.mount_center_offset,
        params.motor.mount_center_offset,
    ):
        shell = shell.cut(
            _x_axis_cylinder(
                enclosure.motor_mount_hole_diameter / 2,
                side_cut_length,
                left_outer_x - EPSILON,
                mount_y,
                -params.motor.shaft_offset,
            )
        )
    return shell.val().clean()


def _enclosure_half(
    upper: bool,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    enclosure = params.drum_enclosure
    half_height = (params.enclosure_outer_height - enclosure.split_gap) / 2
    split_z = enclosure.split_gap / 2
    center_z = split_z + half_height / 2
    if not upper:
        center_z = -center_z

    clipping_box = (
        cq.Workplane("XY", origin=(0, 0, center_z))
        .box(
            params.enclosure_overall_width + 2,
            2 * params.enclosure_outer_depth,
            half_height,
        )
        .val()
    )
    result = _drum_enclosure_shell(params).intersect(clipping_box)
    return result.clean()


def drum_enclosure_upper(params: DesignParameters = DESIGN) -> cq.Shape:
    """Upper printable shell prepared for a future embedded-magnet joint."""

    return _enclosure_half(True, params)


def drum_enclosure_lower(params: DesignParameters = DESIGN) -> cq.Shape:
    """Symmetric lower shell prepared for a future embedded-magnet joint."""

    return _enclosure_half(False, params)


def drum_enclosure_parts(
    params: DesignParameters = DESIGN,
) -> dict[str, cq.Shape]:
    """The complete rear-open enclosure as exactly two printable solids."""

    return {
        "enclosure_upper": drum_enclosure_upper(params),
        "enclosure_lower": drum_enclosure_lower(params),
    }
