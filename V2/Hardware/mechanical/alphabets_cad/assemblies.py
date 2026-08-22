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
CAPTURE_FLOOR = cq.Color(0.12, 0.45, 0.8, 0.22)
CAPTURE_ENVELOPE = cq.Color(0.15, 0.8, 0.65, 0.55)


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


def _captured_transform(shape: cq.Shape, capture: dict[str, Any]) -> cq.Shape:
    """Apply a Blender rigid transform in millimetres without matrix shear."""

    quaternion = [float(value) for value in capture["rotation_quaternion_wxyz"]]
    norm = math.sqrt(sum(value * value for value in quaternion))
    if norm == 0:
        raise ValueError(f"zero quaternion for {capture['name']}")
    w, x, y, z = (value / norm for value in quaternion)
    if w < 0:
        w, x, y, z = (-w, -x, -y, -z)
    angle = 2 * math.acos(max(-1.0, min(1.0, w)))
    denominator = math.sqrt(max(0.0, 1 - w * w))
    axis = (
        (1.0, 0.0, 0.0)
        if denominator < 1e-12
        else (
            x / denominator,
            y / denominator,
            z / denominator,
        )
    )
    return shape.rotate((0, 0, 0), axis, math.degrees(angle)).translate(
        tuple(float(value) for value in capture["origin_world_mm"])
    )


def _captured_card_components_from_data(
    data: dict[str, Any],
    params: DesignParameters,
) -> tuple[Component, ...]:
    card_at_pivot = _card_layer_at_pivot(flap_card(params), params)
    center = card_at_pivot.Center()
    center_offset = (-center.x, -center.y, -center.z)
    card_centered = card_at_pivot.translate(center_offset)
    stickers_centered = {
        face: _card_layer_at_pivot(shape, params).translate(center_offset)
        for face, shape in flap_sticker_layers(params).items()
    }

    components: list[Component] = []
    for capture in data["cards"]:
        number = int(capture["card_number"])
        components.append(
            Component(
                name=f"card_{number:02d}",
                shape=_captured_transform(card_centered, capture),
                color=FLAP,
            )
        )
        components.extend(
            Component(
                name=f"sticker_{number:02d}_{face}",
                shape=_captured_transform(shape, capture),
                color=STICKER,
            )
            for face, shape in stickers_centered.items()
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
    floor_bounds = data["floor"]["bounds_world_mm"]
    card_bounds = data["all_cards_bounds_world_mm"]
    floor_minimum = (
        card_bounds["minimum"][0] - 5,
        card_bounds["minimum"][1] - 5,
        floor_bounds["maximum"][2] - 0.5,
    )
    floor_maximum = (
        card_bounds["maximum"][0] + 5,
        floor_bounds["maximum"][1],
        floor_bounds["maximum"][2],
    )
    floor_lengths = [floor_maximum[axis] - floor_minimum[axis] for axis in range(3)]
    floor_center = [
        (floor_maximum[axis] + floor_minimum[axis]) / 2 for axis in range(3)
    ]
    floor = cq.Workplane("XY").box(*floor_lengths).translate(tuple(floor_center)).val()
    pawl_bounds = data["pawl"]["bounds_world_mm"]
    pawl_lengths = [
        pawl_bounds["maximum"][axis] - pawl_bounds["minimum"][axis] for axis in range(3)
    ]
    pawl_center = [
        (pawl_bounds["maximum"][axis] + pawl_bounds["minimum"][axis]) / 2
        for axis in range(3)
    ]
    pawl = cq.Workplane("XY").box(*pawl_lengths).translate(tuple(pawl_center)).val()
    return (
        Component("capture_floor_reference", floor, CAPTURE_FLOOR),
        Component("capture_pawl_reference", pawl, SUPPORT),
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
    """Captured mechanism and references, intentionally without an enclosure."""

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
            ).rotate((0, 0, 0), (1, 0, 0), capture_rotation)
            if name == "motor_shaft"
            else _orient_for_enclosure(shape, motor_offset),
            color=motor_colors[name],
        )
        for name, shape in motor_components(params).items()
    )
    return (
        *drum,
        *_captured_card_components_from_data(data, params),
        *motor,
        *_capture_reference_components(data),
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
