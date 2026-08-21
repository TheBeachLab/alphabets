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
    flap_sticker_layers,
    laser_cut_disc,
    motor_components,
)

ACRYLIC = cq.Color(0.12, 0.12, 0.14, 0.75)
SUPPORT = cq.Color(1.0, 0.45, 0.05, 0.85)
MOTOR = cq.Color(0.65, 0.65, 0.68)
SHAFT = cq.Color(0.95, 0.72, 0.1)
BACKPACK = cq.Color(0.08, 0.23, 0.75)
ENCLOSURE = cq.Color(0.025, 0.025, 0.03)
FLAP = cq.Color(0.015, 0.015, 0.018)
STICKER = cq.Color(1.0, 0.8, 0.0)


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
    """All 64 flap cards in radial startup poses on the stopped drum.

    Every card points away from the drum axis while its tab axis remains centred
    in the corresponding hole. This is the deterministic initial state for a
    later gravity simulation, not the cards' final resting configuration.
    """

    card = params.card
    drum = params.drum
    step_degrees = 360.0 / drum.positions
    stop_degrees = drum_stop_rotation_degrees(params)
    front_upper_position = drum.positions // 2 - 1

    # Put the centre of the card's tab edge at the pivot before mapping it to
    # the enclosure coordinate system: X is the axle, Y is depth and Z height.
    def place_at_pivot(shape: cq.Shape) -> cq.Shape:
        return (
            shape.translate((-card.body_width / 2, -card.tab_axis_height, 0))
            .rotate((0, 0, 0), (1, 0, 0), 90)
            # The finished 0.7 mm stack is centred around the 0.5 mm blank's
            # mid-plane, so this centres every layer through the hole axis.
            .translate((0, card.thickness / 2, 0))
        )

    card_at_pivot = place_at_pivot(flap_card(params))
    stickers_at_pivot = {
        face: place_at_pivot(shape)
        for face, shape in flap_sticker_layers(params).items()
    }

    def mount(
        shape: cq.Shape,
        tilt_degrees: float,
        pivot_depth: float,
        pivot_height: float,
    ) -> cq.Shape:
        return (
            shape.rotate((0, 0, 0), (1, 0, 0), tilt_degrees)
            .translate((0, pivot_depth, pivot_height))
            .clean()
        )

    cards: list[Component] = []
    for position in range(drum.positions):
        angle_degrees = 180.0 - stop_degrees - position * step_degrees
        angle_radians = math.radians(angle_degrees)
        pivot_depth = drum.flap_hole_center_radius * math.cos(angle_radians)
        pivot_height = drum.flap_hole_center_radius * math.sin(angle_radians)
        # At zero tilt the free edge points down. Rotating by angle + 90 maps
        # that vector onto the radius through this pivot, pointing outwards.
        tilt_degrees = angle_degrees + 90.0
        card_number = (position - front_upper_position) % drum.positions

        cards.append(
            Component(
                name=f"card_{card_number:02d}",
                shape=mount(card_at_pivot, tilt_degrees, pivot_depth, pivot_height),
                color=FLAP,
            )
        )
        cards.extend(
            Component(
                name=f"sticker_{card_number:02d}_{face}",
                shape=mount(shape, tilt_degrees, pivot_depth, pivot_height),
                color=STICKER,
            )
            for face, shape in stickers_at_pivot.items()
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
