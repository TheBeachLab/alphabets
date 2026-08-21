"""Named CadQuery assemblies for fabrication exchange and visual review."""

from __future__ import annotations

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
            shape=_orient_for_enclosure(component.shape, drum_offset),
            color=component.color,
        )
        for component in drum_components(params)
    )

    display_flap = (
        flap_card(params)
        .rotate((0, 0, 0), (1, 0, 0), 90)
        .translate(
            (
                -params.card.body_width / 2,
                -params.drum.radius,
                -params.card.total_height / 2,
            )
        )
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
            shape=_orient_for_enclosure(shape, motor_offset),
            color=motor_colors[name],
        )
        for name, shape in motor_components(params).items()
    )
    return (
        *enclosure_components(params, exploded=exploded),
        *drum,
        Component(name="display_flap", shape=display_flap, color=FLAP),
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
