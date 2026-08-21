"""Named CadQuery assemblies for fabrication exchange and visual review."""

from __future__ import annotations

import math
from dataclasses import dataclass

import cadquery as cq

from .parameters import DESIGN, DesignParameters
from .parts import (
    drum_enclosure_parts,
    drum_support,
    flap_card,
    laser_cut_disc,
    motor_components,
)

ACRYLIC = cq.Color(0.12, 0.12, 0.14, 0.75)
SUPPORT = cq.Color(1.0, 0.45, 0.05, 0.85)
MOTOR = cq.Color(0.65, 0.65, 0.68)
SHAFT = cq.Color(0.95, 0.72, 0.1)
BACKPACK = cq.Color(0.08, 0.23, 0.75)
ENCLOSURE = cq.Color(0.025, 0.025, 0.03)
FLAP = cq.Color(0.92, 0.92, 0.88)


@dataclass(frozen=True)
class Component:
    """One named, independently visible component of a CAD assembly."""

    name: str
    shape: cq.Shape
    color: cq.Color


def _assembly_from_components(
    name: str, components: tuple[Component, ...]
) -> cq.Assembly:
    assembly = cq.Assembly(name=name)
    for component in components:
        assembly.add(component.shape, name=component.name, color=component.color)
    return assembly


def drum_component_shapes(
    params: DesignParameters = DESIGN,
) -> dict[str, cq.Shape]:
    drum = params.drum
    support = drum_support(params)
    support_z = drum.side_thickness + params.drum_inner_width / 2
    rotated_support = support.rotate((0, 0, 0), (1, 0, 0), 90).translate(
        (0, 0, support_z)
    )
    return {
        "motor_side": laser_cut_disc(True, params),
        "shaft_side": laser_cut_disc(False, params).translate(
            (0, 0, drum.side_thickness + params.drum_inner_width)
        ),
        "support_front": rotated_support.translate(
            (0, -drum.support_y + drum.side_thickness / 2, 0)
        ),
        "support_back": rotated_support.translate(
            (0, drum.support_y + drum.side_thickness / 2, 0)
        ),
    }


def drum_components(params: DesignParameters = DESIGN) -> tuple[Component, ...]:
    """Individually inspectable components of the laser-cut drum."""

    return tuple(
        Component(
            name=name,
            shape=shape,
            color=ACRYLIC if "side" in name else SUPPORT,
        )
        for name, shape in drum_component_shapes(params).items()
    )


def drum_assembly(params: DesignParameters = DESIGN) -> cq.Assembly:
    return _assembly_from_components("alphabets-v2-drum", drum_components(params))


def module_reference_components(
    params: DesignParameters = DESIGN,
) -> tuple[Component, ...]:
    """Individually inspectable drum and 28BYJ-48 reference components."""

    colors = {
        "motor_body": MOTOR,
        "motor_collar": MOTOR,
        "motor_backpack": BACKPACK,
        "motor_shaft": SHAFT,
    }
    return (
        *drum_components(params),
        *(
            Component(name=name, shape=shape, color=colors[name])
            for name, shape in motor_components(params).items()
        ),
    )


def module_reference_assembly(
    params: DesignParameters = DESIGN,
) -> cq.Assembly:
    """Known drum geometry plus the dimensioned 28BYJ-48 reference motor."""

    return _assembly_from_components(
        "alphabets-v2-module-reference", module_reference_components(params)
    )


def _orient_for_enclosure(shape: cq.Shape, axial_offset: float) -> cq.Shape:
    """Map drum Z to enclosure X, drum X to depth and drum Y to height."""

    return (
        shape.rotate((0, 0, 0), (0, 1, 0), 90)
        .rotate((0, 0, 0), (1, 0, 0), 90)
        .translate((axial_offset, 0, 0))
    )


def drum_stop_rotation_degrees(params: DesignParameters = DESIGN) -> float:
    """Half a flap pitch, placing the two front pivots above and below centre."""

    return 180.0 / params.drum.positions


def _rotate_drum_to_stop(
    shape: cq.Shape, params: DesignParameters = DESIGN
) -> cq.Shape:
    """Rotate a drum-mounted part around its physical axle to the card stop."""

    return shape.rotate((0, 0, 0), (0, 0, 1), drum_stop_rotation_degrees(params))


def mounted_card_components(
    params: DesignParameters = DESIGN,
) -> tuple[Component, ...]:
    """All 64 flap cards in their stopped, gravity-supported reference poses.

    The lower/front card falls vertically. Upper cards follow the support stack
    from the rear to the front; the front upper card is held vertically by the
    pawl. This is a clearance and enclosure-design reference, not a motion
    simulation or a manufacturing part.
    """

    card = params.card
    drum = params.drum
    step_degrees = 360.0 / drum.positions
    stop_degrees = drum_stop_rotation_degrees(params)
    # These are physical card identifiers, not viewer-only numbering. The
    # established stopped display places 31 above the window and 32 below it.
    # Do not renumber the physical flap sequence to relocate this pair.
    front_upper = drum.positions // 2 - 1
    front_lower = drum.positions // 2
    # Put the centre of the card's tab edge at the pivot before mapping it to
    # the enclosure coordinate system: X is the axle, Y is depth and Z height.
    card_at_pivot = (
        flap_card(params)
        .translate((-card.body_width / 2, -card.tab_axis_height, 0))
        .rotate((0, 0, 0), (1, 0, 0), 90)
        # The card is extruded from z=0 to its material thickness. Once mapped
        # into the enclosure that thickness lies on Y, so move it half a
        # thickness to centre the tab through the flap-hole axis rather than
        # leaving one face on it.
        .translate((0, card.thickness / 2, 0))
    )

    cards: list[Component] = []
    for position in range(drum.positions):
        angle_degrees = 180.0 - stop_degrees - position * step_degrees
        angle_radians = math.radians(angle_degrees)
        pivot_depth = drum.flap_hole_center_radius * math.cos(angle_radians)
        pivot_height = drum.flap_hole_center_radius * math.sin(angle_radians)
        # Every southern card falls with gravity. Northern cards form the
        # rear-to-front support stack. At the stop, both front cards are exact
        # verticals: the lower one falls, the upper one rests on the pawl.
        if position in (front_upper, front_lower) or pivot_height < 0:
            tilt_degrees = 0.0
        else:
            tilt_degrees = angle_degrees - 180.0
        cards.append(
            Component(
                name=f"card_{position:02d}",
                shape=(
                    card_at_pivot.rotate((0, 0, 0), (1, 0, 0), tilt_degrees)
                    .translate((0, pivot_depth, pivot_height))
                    .clean()
                ),
                color=FLAP,
            )
        )
    return tuple(cards)


def enclosure_components(
    params: DesignParameters = DESIGN,
    *,
    exploded: bool = False,
) -> tuple[Component, ...]:
    """Individually inspectable printable enclosure halves."""

    separation = 10.0 if exploded else 0.0
    parts = drum_enclosure_parts(params)
    return (
        Component(
            name="enclosure_upper",
            shape=parts["enclosure_upper"].translate((0, 0, separation)),
            color=ENCLOSURE,
        ),
        Component(
            name="enclosure_lower",
            shape=parts["enclosure_lower"].translate((0, 0, -separation)),
            color=ENCLOSURE,
        ),
    )


def enclosure_assembly(
    params: DesignParameters = DESIGN,
    *,
    exploded: bool = False,
) -> cq.Assembly:
    """The two printable enclosure halves in assembled or exploded position."""

    return _assembly_from_components(
        "alphabets-v2-drum-enclosure", enclosure_components(params, exploded=exploded)
    )


def enclosed_module_components(
    params: DesignParameters = DESIGN,
    *,
    exploded: bool = False,
) -> tuple[Component, ...]:
    """Individually inspectable rear-open enclosure, drum and motor parts."""

    drum_offset = -params.drum_outer_width / 2
    drum = tuple(
        Component(
            name=component.name,
            shape=_orient_for_enclosure(
                _rotate_drum_to_stop(component.shape, params), drum_offset
            ),
            color=component.color,
        )
        for component in drum_components(params)
    )
    motor_offset = -params.enclosure_outer_width / 2
    motor_colors = {
        "motor_body": MOTOR,
        "motor_collar": MOTOR,
        "motor_backpack": BACKPACK,
        "motor_shaft": SHAFT,
    }
    motor = tuple(
        Component(
            name=name,
            shape=_orient_for_enclosure(
                shape.rotate((0, 0, 0), (0, 0, 1), 90)
                if name == "motor_shaft"
                else shape,
                motor_offset,
            ),
            color=motor_colors[name],
        )
        for name, shape in motor_components(params).items()
    )
    return (
        *enclosure_components(params, exploded=exploded),
        *drum,
        *mounted_card_components(params),
        *motor,
    )


def enclosed_module_assembly(
    params: DesignParameters = DESIGN,
    *,
    exploded: bool = False,
) -> cq.Assembly:
    """Rear-open enclosure, current drum and externally mounted motor."""

    return _assembly_from_components(
        "alphabets-v2-enclosed-module",
        enclosed_module_components(params, exploded=exploded),
    )
