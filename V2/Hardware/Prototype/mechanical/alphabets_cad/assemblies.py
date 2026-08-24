# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Named CadQuery assemblies for fabrication exchange and visual review."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cadquery as cq

from .parameters import DESIGN, DesignParameters
from .parts import (
    _captured_electronics_card_envelope,
    captured_drum_enclosure_parts,
    captured_enclosure_limits,
    captured_pawl_parts,
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
CAPTURED_ENCLOSURE = cq.Color(0.08, 0.1, 0.14, 1.0)
PAWL = cq.Color(0.28, 0.31, 0.36, 1.0)
FLAP = cq.Color(0.015, 0.015, 0.018)
STICKER = cq.Color(1.0, 0.8, 0.0)
CAPTURE_ENVELOPE = cq.Color(0.15, 0.8, 0.65, 0.55)
ELECTRONICS = cq.Color(0.08, 0.55, 0.2, 0.75)


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


def _card_layer_at_pivot(
    shape: cq.Shape,
    params: DesignParameters = DESIGN,
) -> cq.Shape:
    """Map a card layer into enclosure axes with its tab axis at the origin."""

    card = params.card
    return (
        shape.translate((-card.body_width / 2, -card.tab_axis_height, 0))
        .rotate((0, 0, 0), (1, 0, 0), 90)
        .translate((0, card.thickness / 2, 0))
    )


def mounted_card_components(
    params: DesignParameters = DESIGN,
) -> tuple[Component, ...]:
    """All 64 flap cards in radial startup poses on the stopped drum.

    Every card points away from the drum axis while its tab axis remains centred
    in the corresponding hole. This is the deterministic initial state for a
    later gravity simulation, not the cards' final resting configuration.
    """

    drum = params.drum
    step_degrees = 360.0 / drum.positions
    stop_degrees = drum_stop_rotation_degrees(params)
    front_lower_position = drum.positions // 2

    card_at_pivot = _card_layer_at_pivot(flap_card(params), params)
    stickers_at_pivot = {
        face: _card_layer_at_pivot(shape, params)
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
        # Number in the observed direction of travel from the motor-side view:
        # card 00 is the lower-front card, card 01 the upper-front card, and
        # card 02 is the next card arriving as the drum turns anticlockwise.
        card_number = (front_lower_position - position) % drum.positions

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


def load_card_capture(path: Path) -> dict[str, Any]:
    """Load and validate one 64-card Blender simulation snapshot."""

    data = json.loads(path.read_text(encoding="utf-8"))
    cards = data.get("cards", [])
    numbers = [card.get("card_number") for card in cards]
    if data.get("schema_version") != 1 or numbers != list(range(64)):
        raise ValueError(f"invalid 64-card capture: {path}")
    return data


def _captured_card_x_rotation_degrees(capture: dict[str, Any]) -> float:
    """Return the captured flap angle around the physical drum axis only."""

    matrix = capture["matrix_world"]
    return math.degrees(math.atan2(float(matrix[2][1]), float(matrix[1][1])))


def _captured_hole_center(
    card_number: int,
    capture_rotation_degrees: float,
    params: DesignParameters = DESIGN,
) -> tuple[float, float, float]:
    """Exact world centre of one card's drum hole in the captured position."""

    drum = params.drum
    if not 0 <= card_number < drum.positions:
        raise ValueError(f"card number outside drum: {card_number}")
    step_degrees = 360.0 / drum.positions
    source_hole_position = (drum.positions // 2 - card_number) % drum.positions
    initial_angle = math.radians(
        180.0 - drum_stop_rotation_degrees(params) - source_hole_position * step_degrees
    )
    initial_y = drum.flap_hole_center_radius * math.cos(initial_angle)
    initial_z = drum.flap_hole_center_radius * math.sin(initial_angle)
    capture_angle = math.radians(capture_rotation_degrees)
    return (
        0.0,
        initial_y * math.cos(capture_angle) - initial_z * math.sin(capture_angle),
        initial_y * math.sin(capture_angle) + initial_z * math.cos(capture_angle),
    )


def _place_captured_card_layer(
    shape_at_pivot: cq.Shape,
    capture: dict[str, Any],
    hole_center: tuple[float, float, float],
) -> cq.Shape:
    """Preserve captured flap tilt while snapping its tab axis to the hole."""

    return shape_at_pivot.rotate(
        (0, 0, 0),
        (1, 0, 0),
        _captured_card_x_rotation_degrees(capture),
    ).translate(hole_center)


def _captured_card_components_from_data(
    data: dict[str, Any],
    params: DesignParameters,
) -> tuple[Component, ...]:
    card_at_pivot = _card_layer_at_pivot(flap_card(params), params)
    stickers_at_pivot = {
        face: _card_layer_at_pivot(shape, params)
        for face, shape in flap_sticker_layers(params).items()
    }
    capture_rotation = float(data["controller"]["rotation_x_degrees"])

    components: list[Component] = []
    for capture in data["cards"]:
        number = int(capture["card_number"])
        hole_center = _captured_hole_center(number, capture_rotation, params)
        components.append(
            Component(
                name=f"card_{number:02d}",
                shape=_place_captured_card_layer(
                    card_at_pivot,
                    capture,
                    hole_center,
                ),
                color=FLAP,
            )
        )
        components.extend(
            Component(
                name=f"sticker_{number:02d}_{face}",
                shape=_place_captured_card_layer(shape, capture, hole_center),
                color=STICKER,
            )
            for face, shape in stickers_at_pivot.items()
        )
    return tuple(components)


def captured_card_components(
    capture_path: Path,
    params: DesignParameters = DESIGN,
) -> tuple[Component, ...]:
    """Cards and sticker solids transformed to a captured Blender resting pose."""

    return _captured_card_components_from_data(load_card_capture(capture_path), params)


def _bounds_frame(
    name: str,
    bounds: dict[str, list[float]],
    color: cq.Color,
    edge: float = 0.35,
) -> Component:
    minimum = bounds["minimum"]
    maximum = bounds["maximum"]
    lengths = [maximum[index] - minimum[index] for index in range(3)]
    center = [(maximum[index] + minimum[index]) / 2 for index in range(3)]
    solids: list[cq.Shape] = []
    for axis in range(3):
        dimensions = [edge, edge, edge]
        dimensions[axis] = lengths[axis]
        other_axes = [index for index in range(3) if index != axis]
        for first in (minimum[other_axes[0]], maximum[other_axes[0]]):
            for second in (minimum[other_axes[1]], maximum[other_axes[1]]):
                location = center.copy()
                location[other_axes[0]] = first
                location[other_axes[1]] = second
                solids.append(
                    cq.Workplane("XY").box(*dimensions).translate(tuple(location)).val()
                )
    return Component(
        name=name,
        shape=cq.Compound.makeCompound(solids),
        color=color,
    )


def _capture_reference_components(data: dict[str, Any]) -> tuple[Component, ...]:
    """Card envelopes retained for fit review without Blender floor/pawl solids."""

    return (
        _bounds_frame(
            "capture_southern_cards_envelope",
            data["southern_cards_bounds_world_mm"],
            CAPTURE_ENVELOPE,
        ),
        _bounds_frame(
            "capture_all_cards_envelope",
            data["all_cards_bounds_world_mm"],
            cq.Color(0.8, 0.25, 0.2, 0.4),
        ),
    )


def captured_enclosure_design_components(
    capture_path: Path,
    params: DesignParameters = DESIGN,
) -> tuple[Component, ...]:
    """Captured mechanism inside its fitted two-part enclosure."""

    data = load_card_capture(capture_path)
    capture_rotation = float(data["controller"]["rotation_x_degrees"])
    drum_offset = -params.drum_outer_width / 2
    drum = tuple(
        Component(
            name=component.name,
            shape=_orient_for_enclosure(
                _rotate_drum_to_stop(component.shape, params), drum_offset
            ).rotate((0, 0, 0), (1, 0, 0), capture_rotation),
            color=component.color,
        )
        for component in drum_components(params)
    )

    motor_offset = (
        captured_enclosure_limits(data, params).outer_x_min
        + params.drum_enclosure.side_inset_depth
    )
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
            ).rotate((0, 0, 0), (1, 0, 0), capture_rotation)
            if name == "motor_shaft"
            else _orient_for_enclosure(shape, motor_offset),
            color=motor_colors[name],
        )
        for name, shape in motor_components(params).items()
    )
    enclosure = tuple(
        Component(name=name, shape=shape, color=CAPTURED_ENCLOSURE)
        for name, shape in captured_drum_enclosure_parts(data, params).items()
    )
    pawls = tuple(
        Component(name=name, shape=shape, color=PAWL)
        for name, shape in captured_pawl_parts(data, params).items()
    )
    electronics = Component(
        name="electronics_card_envelope",
        shape=_captured_electronics_card_envelope(
            captured_enclosure_limits(data, params),
            params,
        ),
        color=ELECTRONICS,
    )
    return (
        *enclosure,
        *pawls,
        *drum,
        *_captured_card_components_from_data(data, params),
        *motor,
        electronics,
        *_capture_reference_components(data),
    )
