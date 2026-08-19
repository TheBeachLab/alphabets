"""Named CadQuery assemblies for fabrication exchange and visual review."""

from __future__ import annotations

import cadquery as cq

from .parameters import DESIGN, DesignParameters
from .parts import drum_support, laser_cut_disc, motor_components

ACRYLIC = cq.Color(0.12, 0.12, 0.14, 0.75)
SUPPORT = cq.Color(1.0, 0.45, 0.05, 0.85)
MOTOR = cq.Color(0.65, 0.65, 0.68)
SHAFT = cq.Color(0.95, 0.72, 0.1)
BACKPACK = cq.Color(0.08, 0.23, 0.75)


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


def drum_assembly(params: DesignParameters = DESIGN) -> cq.Assembly:
    assembly = cq.Assembly(name="alphabets-v2-drum")
    for name, shape in drum_component_shapes(params).items():
        assembly.add(
            shape,
            name=name,
            color=ACRYLIC if "side" in name else SUPPORT,
        )
    return assembly


def module_reference_assembly(
    params: DesignParameters = DESIGN,
) -> cq.Assembly:
    """Known drum geometry plus the dimensioned 28BYJ-48 reference motor."""

    assembly = cq.Assembly(name="alphabets-v2-module-reference")
    for name, shape in drum_component_shapes(params).items():
        assembly.add(
            shape,
            name=name,
            color=ACRYLIC if "side" in name else SUPPORT,
        )
    colors = {
        "motor_body": MOTOR,
        "motor_collar": MOTOR,
        "motor_backpack": BACKPACK,
        "motor_shaft": SHAFT,
    }
    for name, shape in motor_components(params).items():
        assembly.add(shape, name=name, color=colors[name])
    return assembly
