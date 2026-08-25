# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import math
import re
import runpy
from fractions import Fraction
from pathlib import Path

import cadquery as cq
import ezdxf
import pytest

from alphabets_cad.assemblies import (
    captured_card_components,
    captured_enclosure_design_components,
    drum_component_shapes,
    drum_stop_rotation_degrees,
    module_reference_assembly,
    module_reference_components,
    mounted_card_components,
)
from alphabets_cad.export import (
    A1_MINI_BUILD_VOLUME_MM,
    A1_MINI_PLATE_MARGIN_MM,
    _captured_bambu_a1_mini_plate,
)
from alphabets_cad.parameters import DESIGN, load_design_profile
from alphabets_cad.parts import (
    ALPHA_FONT_PATH,
    _captured_alignment_frustums,
    _captured_docking_recess,
    _captured_electronics_card_envelope,
    _captured_magnet_pockets,
    _captured_motor_mount_bosses,
    _captured_motor_mount_pilots,
    _captured_motor_mount_pocket,
    _captured_pawl_mount,
    _captured_pawl_pilot,
    _captured_pawl_screw_axis_z,
    _captured_shaft_head_recess,
    _captured_shaft_support,
    _captured_stack_alignment_frustums,
    _captured_stack_magnet_pocket,
    _captured_top_alpha_cutter,
    captured_drum_enclosure_parts,
    captured_enclosure_limits,
    captured_pawl_parts,
    card_points,
    drum_support,
    enclosure_reference_edges,
    finished_flap_card,
    flap_card,
    flap_sticker_layers,
    laser_cut_disc,
    legacy_holder_side,
    motor_components,
    printed_spool_disc,
)

MECHANICAL_DIR = Path(__file__).resolve().parents[1]
FINAL_DIR = MECHANICAL_DIR.parent
HARDWARE_DIR = FINAL_DIR.parent
PROTOTYPE_DIR = HARDWARE_DIR / "Prototype"
REPO_ROOT = HARDWARE_DIR.parents[1]
GENERATED = MECHANICAL_DIR / "generated"
CARD_CAPTURE = FINAL_DIR / "blender/generated/cards-position-capture.json"


def assert_bounds(
    shape: cq.Shape,
    expected: tuple[float, float, float],
    tolerance: float = 1e-6,
) -> None:
    box = shape.BoundingBox()
    assert box.xlen == pytest.approx(expected[0], abs=tolerance)
    assert box.ylen == pytest.approx(expected[1], abs=tolerance)
    assert box.zlen == pytest.approx(expected[2], abs=tolerance)


def test_current_source_parameters_are_centralized_without_drift() -> None:
    spool = (PROTOTYPE_DIR / "structure/spool.scad").read_text(encoding="utf-8")
    for name, value in {
        "ncards": DESIGN.drum.positions,
        "sdiam": DESIGN.drum.diameter,
        "e": DESIGN.drum.side_thickness,
        "kerf": DESIGN.drum.laser_kerf,
        "flap_width": DESIGN.card.body_width,
        "axial_clearance": DESIGN.drum.axial_clearance,
        "shaft_axis_radius": DESIGN.drum.shaft_axis_radius,
        "w": DESIGN.drum.support_width,
        "tabw": DESIGN.drum.support_tab_width,
    }.items():
        match = re.search(rf"(?m)^\s*{name}\s*=\s*([0-9.]+)\s*;", spool)
        assert match, name
        assert float(match.group(1)) == pytest.approx(float(value))

    card_manifest = json.loads(
        (FINAL_DIR / "cards/card-50x48.json").read_text(encoding="utf-8")
    )
    assert card_manifest["card_mm"]["body_width"] == DESIGN.card.body_width
    assert card_manifest["card_mm"]["total_height"] == DESIGN.card.total_height
    assert card_manifest["drum_mm"]["inner_width"] == DESIGN.drum_inner_width

    printed_spool = (PROTOTYPE_DIR / "structure/spool-3dp.scad").read_text(
        encoding="utf-8"
    )
    for name, value in {
        "ncards": DESIGN.drum.positions,
        "sdiam": DESIGN.drum.diameter,
        "e": DESIGN.printed_spool.thickness,
    }.items():
        match = re.search(rf"(?m)^\s*{name}\s*=\s*([0-9.]+)\s*;", printed_spool)
        assert match, name
        assert float(match.group(1)) == pytest.approx(float(value))

    motor = (PROTOTYPE_DIR / "structure/28byj48.scad").read_text(encoding="utf-8")
    for name, value in {
        "chassis_radius": DESIGN.motor.chassis_radius,
        "chassis_height": DESIGN.motor.chassis_height,
        "shaft_offset": DESIGN.motor.shaft_offset,
        "mount_center_offset": DESIGN.motor.mount_center_offset,
        "shaft_radius": DESIGN.motor.shaft_radius,
        "shaft_height": DESIGN.motor.shaft_height,
        "backpack_width": DESIGN.motor.backpack_width,
        "backpack_extent": DESIGN.motor.backpack_extent,
        "backpack_height": DESIGN.motor.backpack_height,
    }.items():
        match = re.search(rf"(?m)^\s*{name}\s*=\s*([0-9./]+)\s*;", motor)
        assert match, name
        assert float(Fraction(match.group(1))) == pytest.approx(value)

    card_envelope = json.loads(
        (FINAL_DIR / "blender/generated/card-envelope.json").read_text(encoding="utf-8")
    )
    assert card_envelope["upper"]["distance_from_axis_mm"] == pytest.approx(
        DESIGN.drum_enclosure.upper_card_envelope_height,
        abs=1e-6,
    )
    assert card_envelope["drum_radius_mm"] == pytest.approx(
        DESIGN.drum.radius,
        abs=1e-5,
    )


def test_flap_card_matches_current_cutter_geometry() -> None:
    card = flap_card()
    assert card.isValid()
    assert_bounds(
        card,
        (DESIGN.card.overall_width, DESIGN.card.total_height, DESIGN.card.thickness),
    )
    assert card.Volume() == pytest.approx(
        (
            DESIGN.card.body_width * DESIGN.card.total_height
            + 2 * DESIGN.card.tab_width * DESIGN.card.tab_height
        )
        * DESIGN.card.thickness
    )
    assert card_points()[0] == (0.0, 0.0)
    assert card_points()[5] == (-DESIGN.card.tab_width, DESIGN.card.total_height)
    assert DESIGN.card.tab_start_height == pytest.approx(45.5)
    assert DESIGN.card.tab_axis_height == pytest.approx(46.75)
    assert DESIGN.card.tab_rotation_radius == pytest.approx(
        math.sqrt(1.25**2 + 0.25**2)
    )
    assert DESIGN.card.finished_thickness == pytest.approx(0.7)
    assert DESIGN.card.sticker_side_margin == pytest.approx(2.5)
    assert DESIGN.card.sticker_y_offset == pytest.approx(DESIGN.card.tab_height)
    assert DESIGN.flap_tab_radial_clearance >= DESIGN.drum.flap_rotation_clearance


def test_finished_flap_card_includes_two_sticker_layers() -> None:
    card = finished_flap_card()
    assert card.isValid()
    assert_bounds(
        card,
        (
            DESIGN.card.overall_width,
            DESIGN.card.total_height,
            DESIGN.card.finished_thickness,
        ),
    )
    assert card.Volume() == pytest.approx(
        flap_card().Volume()
        + 2
        * DESIGN.card.sticker_width
        * DESIGN.card.sticker_face_height
        * DESIGN.card.sticker_face_thickness
    )
    assert not card.isInside(cq.Vector(25, 1, -0.05), 1e-6)
    assert card.isInside(cq.Vector(25, 47, -0.05), 1e-6)
    stickers = flap_sticker_layers()
    assert tuple(stickers) == ("front", "back")
    assert all(
        sticker.BoundingBox().ymin == pytest.approx(DESIGN.card.sticker_y_offset)
        for sticker in stickers.values()
    )


@pytest.mark.parametrize("motor_side", [True, False])
def test_laser_cut_disc_is_valid_and_has_64_flap_holes(motor_side: bool) -> None:
    disc = laser_cut_disc(motor_side)
    assert disc.isValid()
    assert_bounds(
        disc,
        (DESIGN.drum.diameter, DESIGN.drum.diameter, DESIGN.drum.side_thickness),
    )
    downward_face = min(disc.Faces(), key=lambda face: face.Center().z)
    assert len(downward_face.innerWires()) == 69
    if not motor_side:
        assert not disc.isInside(
            cq.Vector(DESIGN.drum.shaft_axis_radius - 0.05, 0, 1),
            1e-6,
        )
        assert disc.isInside(
            cq.Vector(DESIGN.drum.shaft_axis_radius + 0.05, 0, 1),
            1e-6,
        )


def test_supports_define_the_exact_51_mm_inner_and_55_3_mm_outer_width() -> None:
    support = drum_support()
    assert support.isValid()
    assert_bounds(
        support,
        (
            DESIGN.drum.support_width,
            DESIGN.drum_inner_width + 2 * DESIGN.drum.side_thickness,
            DESIGN.drum.side_thickness,
        ),
    )
    components = drum_component_shapes()
    compound = cq.Compound.makeCompound(list(components.values()))
    assert_bounds(
        compound,
        (DESIGN.drum.diameter, DESIGN.drum.diameter, DESIGN.drum_outer_width),
    )


def test_drum_tabs_reproduce_the_laser_kerf_press_fit() -> None:
    shapes = drum_component_shapes()
    assert shapes["support_front"].intersect(
        shapes["support_back"]
    ).Volume() == pytest.approx(0)
    drum = DESIGN.drum
    expected_overlap = (
        2
        * (
            drum.support_tab_width * drum.side_thickness
            - (drum.support_tab_width - 2 * drum.laser_kerf)
            * (drum.side_thickness - 2 * drum.laser_kerf)
        )
        * drum.side_thickness
    )
    for support_name in ("support_front", "support_back"):
        for side_name in ("motor_side", "shaft_side"):
            overlap = shapes[support_name].intersect(shapes[side_name]).Volume()
            assert overlap == pytest.approx(expected_overlap, abs=1e-5)


def test_printed_spool_variants_reproduce_legacy_envelopes() -> None:
    motor_side = printed_spool_disc(True)
    shaft_side = printed_spool_disc(False)
    assert motor_side.isValid()
    assert shaft_side.isValid()
    assert_bounds(
        motor_side,
        (
            DESIGN.drum.diameter,
            DESIGN.drum.diameter,
            DESIGN.printed_spool.thickness,
        ),
    )
    assert_bounds(
        shaft_side,
        (
            DESIGN.drum.diameter,
            DESIGN.drum.diameter,
            DESIGN.printed_spool.shaft_pin_height,
        ),
    )


def test_motor_reference_matches_the_scad_overall_envelope() -> None:
    components = motor_components()
    compound = cq.Compound.makeCompound(list(components.values()))
    assert compound.isValid()
    assert compound.BoundingBox().xmin == pytest.approx(-21.0)
    assert compound.BoundingBox().xmax == pytest.approx(21.0)
    assert compound.BoundingBox().ymin == pytest.approx(-26.0)
    assert compound.BoundingBox().ymax == pytest.approx(6.0)
    assert compound.BoundingBox().zmin == pytest.approx(-19.0)
    assert compound.BoundingBox().zmax == pytest.approx(10.0)


def test_module_reference_contains_known_drum_and_motor_components() -> None:
    assembly = module_reference_assembly()
    names = set(assembly.objects)
    assert names == {
        "alphabets-v2-module-reference",
        "motor_side",
        "shaft_side",
        "support_front",
        "support_back",
        "motor_body",
        "motor_collar",
        "motor_backpack",
        "motor_shaft",
    }
    assert assembly.toCompound().isValid()


def test_module_reference_exposes_individual_colored_components() -> None:
    components = module_reference_components()
    assert tuple(component.name for component in components) == (
        "motor_side",
        "shaft_side",
        "support_front",
        "support_back",
        "motor_body",
        "motor_collar",
        "motor_backpack",
        "motor_shaft",
    )
    assert all(component.shape.isValid() for component in components)
    assert all(len(component.color.toTuple()) == 4 for component in components)


def test_design_profile_applies_direct_values_and_keeps_derived_values() -> None:
    profile = MECHANICAL_DIR / "profiles/fit-check.toml"
    params = load_design_profile(profile, base=DESIGN)
    assert params.drum.axial_clearance == 1.5
    assert params.drum_enclosure.radial_clearance == 2.5
    assert params.drum_inner_width == pytest.approx(51.5)
    assert params.enclosure_inner_height == pytest.approx(DESIGN.enclosure_inner_height)
    assert params.enclosure_inner_depth == pytest.approx(90.0)


def test_design_profile_rejects_unknown_dimension(tmp_path: Path) -> None:
    profile = tmp_path / "invalid.toml"
    profile.write_text("[drum]\nunknown_dimension = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown_dimension"):
        load_design_profile(profile, base=DESIGN)


def test_design_profile_rejects_a_tab_that_cannot_rotate(tmp_path: Path) -> None:
    profile = tmp_path / "blocked-tab.toml"
    profile.write_text("[card]\ntab_height = 3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="required radial clearance"):
        load_design_profile(profile, base=DESIGN)


def test_cq_editor_entry_point_builds_the_reference_module() -> None:
    namespace = runpy.run_path(str(MECHANICAL_DIR / "view.py"))
    result = namespace["result"]
    assert isinstance(result, cq.Assembly)
    assert result.name == "alphabets-v2-module-reference"
    assert result.toCompound().isValid()


def test_cq_editor_entry_point_exposes_profile_and_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = MECHANICAL_DIR / "profiles/fit-check.toml"
    monkeypatch.setenv("ALPHABETS_PROFILE", str(profile))
    namespace = runpy.run_path(str(MECHANICAL_DIR / "view.py"))
    assert namespace["parameters"].drum.axial_clearance == 1.5
    assert set(namespace["objects"]) == {
        "motor_side",
        "shaft_side",
        "support_front",
        "support_back",
        "motor_body",
        "motor_collar",
        "motor_backpack",
        "motor_shaft",
    }


def test_stopped_drum_mounts_all_cards_radially_outward() -> None:
    components = mounted_card_components()
    cards = {
        component.name: component.shape
        for component in components
        if component.name.startswith("card_")
    }
    stickers = {
        component.name: component.shape
        for component in components
        if component.name.startswith("sticker_")
    }
    assert drum_stop_rotation_degrees() == pytest.approx(360 / 64 / 2)
    assert set(cards) == {f"card_{position:02d}" for position in range(64)}
    assert set(stickers) == {
        f"sticker_{position:02d}_{face}"
        for position in range(64)
        for face in ("front", "back")
    }
    assert all(card.isValid() for card in cards.values())
    assert all(
        component.color.toTuple()[:3] == pytest.approx((0.015, 0.015, 0.018))
        for component in components
        if component.name.startswith("card_")
    )
    assert all(
        component.color.toTuple()[:3] == pytest.approx((1.0, 0.8, 0.0))
        for component in components
        if component.name.startswith("sticker_")
    )

    step_degrees = 360 / DESIGN.drum.positions
    stop_degrees = drum_stop_rotation_degrees()
    front_lower_position = DESIGN.drum.positions // 2
    for position in range(DESIGN.drum.positions):
        card_number = (front_lower_position - position) % DESIGN.drum.positions
        card = cards[f"card_{card_number:02d}"]
        angle = math.radians(180 - stop_degrees - position * step_degrees)
        radial_depth = math.cos(angle)
        radial_height = math.sin(angle)
        pivot_depth = DESIGN.drum.flap_hole_center_radius * radial_depth
        pivot_height = DESIGN.drum.flap_hole_center_radius * radial_height
        center = card.Center()
        center_offset_depth = center.y - pivot_depth
        center_offset_height = center.z - pivot_height
        cross = (
            radial_depth * center_offset_height - radial_height * center_offset_depth
        )
        dot = radial_depth * center_offset_depth + radial_height * center_offset_height
        assert cross == pytest.approx(0, abs=1e-6)
        assert dot > 0

    assert cards["card_00"].Center().z < 0
    assert cards["card_01"].Center().z > 0
    assert cards["card_02"].Center().z > cards["card_01"].Center().z


def test_blender_capture_maps_every_card_and_sticker_into_cadquery() -> None:
    capture = json.loads(CARD_CAPTURE.read_text(encoding="utf-8"))
    components = captured_card_components(CARD_CAPTURE)
    shapes = {component.name: component.shape for component in components}
    assert len(components) == 64 * 3
    assert set(shapes) == {
        *(f"card_{number:02d}" for number in range(64)),
        *(
            f"sticker_{number:02d}_{face}"
            for number in range(64)
            for face in ("front", "back")
        ),
    }
    assert all(shape.isValid() for shape in shapes.values())

    for card_capture in capture["cards"]:
        number = card_capture["card_number"]
        box = shapes[f"card_{number:02d}"].BoundingBox()
        expected = card_capture["bounds_world_mm"]
        actual = (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)
        wanted = (*expected["minimum"], *expected["maximum"])
        assert actual == pytest.approx(wanted, abs=2e-5)


def test_capture_design_view_groups_fit_data_without_floor_or_pawl_solids() -> None:
    components = captured_enclosure_design_components(CARD_CAPTURE)
    names = {component.name for component in components}
    assert {
        "enclosure_upper",
        "enclosure_lower",
        "pawl_definitive",
        "pawl_prototype",
        "motor_side",
        "shaft_side",
        "support_front",
        "support_back",
        "motor_shaft",
        "card_00",
        "card_63",
        "capture_southern_cards_envelope",
        "capture_all_cards_envelope",
    } < names
    assert "capture_floor_reference" not in names
    assert "capture_pawl_reference" not in names


def test_captured_enclosure_is_open_ended_tube_with_replaceable_pawls() -> None:
    capture = json.loads(CARD_CAPTURE.read_text(encoding="utf-8"))
    limits = captured_enclosure_limits(capture)
    parts = captured_drum_enclosure_parts(capture)
    assert tuple(parts) == ("enclosure_upper", "enclosure_lower")
    assert all(shape.isValid() for shape in parts.values())
    assert all(len(shape.Solids()) == 1 for shape in parts.values())

    enclosure = DESIGN.drum_enclosure
    assert limits.inner_bottom_z == pytest.approx(-75, abs=1e-5)
    assert limits.back_y == pytest.approx(-68.750377417)
    assert limits.front_y == pytest.approx(40.301814675)
    assert limits.inner_top_z == pytest.approx(68.313832998)
    assert limits.outer_width == pytest.approx(78.01138468)
    assert limits.outer_depth == pytest.approx(109.052192092)
    assert limits.outer_height == pytest.approx(159.313828528)

    upper = parts["enclosure_upper"]
    lower = parts["enclosure_lower"]
    assert upper.BoundingBox().zmin == pytest.approx(
        enclosure.capture_split_height + enclosure.split_gap / 2,
        abs=1e-5,
    )
    assert lower.BoundingBox().zmax == pytest.approx(
        enclosure.capture_split_height
        + enclosure.alignment_height
        - enclosure.split_gap / 2
        + 0.05,
        abs=1e-5,
    )
    assert upper.intersect(lower).Volume() == pytest.approx(0)
    assert upper.BoundingBox().xlen == pytest.approx(limits.outer_width)
    assert lower.BoundingBox().xlen == pytest.approx(limits.outer_width)
    assert lower.BoundingBox().zmin == pytest.approx(
        limits.outer_bottom_z - enclosure.alignment_height,
        abs=1e-5,
    )

    for end_y in (limits.back_y, limits.front_y):
        opening_probe = (
            cq.Workplane("XY").box(20, 1, 80).translate((15, end_y, 0)).val()
        )
        assert upper.intersect(opening_probe).Volume() == pytest.approx(0)
        assert lower.intersect(opening_probe).Volume() == pytest.approx(0)

    pawls = captured_pawl_parts(capture)
    assert tuple(pawls) == ("pawl_definitive", "pawl_prototype")
    assert all(shape.isValid() for shape in pawls.values())
    assert all(len(shape.Solids()) == 1 for shape in pawls.values())

    pawl = _captured_pawl_mount(capture, limits)
    pawl_box = pawl.BoundingBox()
    captured_pawl = capture["pawl"]["bounds_world_mm"]
    assert pawl.isValid()
    assert len(pawl.Solids()) == 1
    assert pawl_box.xlen == pytest.approx(enclosure.pawl_mount_width, abs=1e-5)
    assert pawl_box.ymin == pytest.approx(limits.front_y, abs=1e-5)
    captured_pawl_thickness = (
        capture["pawl"]["bounds_world_mm"]["maximum"][1]
        - capture["pawl"]["bounds_world_mm"]["minimum"][1]
    )
    assert pawl_box.ymax == pytest.approx(
        limits.front_y + captured_pawl_thickness + enclosure.pawl_thickness_addition,
        abs=1e-5,
    )
    assert pawl_box.zmin == pytest.approx(captured_pawl["minimum"][2], abs=1e-5)
    assert pawl_box.zmax == pytest.approx(limits.outer_top_z)
    assert pawls["pawl_prototype"].BoundingBox().zmin == pytest.approx(
        pawl_box.zmin - enclosure.prototype_pawl_extension
    )
    assert upper.intersect(pawl).Volume() == pytest.approx(0)
    assert pawl.isInside(
        cq.Vector(4.8, limits.front_y + 0.5, _captured_pawl_screw_axis_z(limits)),
        1e-6,
    )
    assert not pawl.isInside(
        cq.Vector(
            4.8,
            pawl_box.ymax - 0.1,
            _captured_pawl_screw_axis_z(limits),
        ),
        1e-6,
    )
    assert pawl.isInside(
        cq.Vector(4.8, limits.front_y + 0.5, limits.inner_top_z - 0.5),
        1e-6,
    )
    assert pawl.isInside(
        cq.Vector(
            enclosure.pawl_tip_radius - 0.2,
            limits.front_y + 0.5,
            captured_pawl["minimum"][2] + enclosure.pawl_tip_radius,
        ),
        1e-6,
    )
    assert not pawl.isInside(
        cq.Vector(
            enclosure.pawl_head_recess_diameter / 2 - 0.2,
            pawl_box.ymax - enclosure.pawl_head_recess_depth / 2,
            _captured_pawl_screw_axis_z(limits),
        ),
        1e-6,
    )
    assert pawl.isInside(
        cq.Vector(
            enclosure.pawl_head_recess_diameter / 2 - 0.2,
            limits.front_y + 0.5,
            _captured_pawl_screw_axis_z(limits),
        ),
        1e-6,
    )

    # The 4 mm treatment chamfers only the inner front rim and restores a flat
    # land around the replaceable pawl; the outside front edge stays square.
    assert upper.isInside(
        cq.Vector(6, limits.front_y - 0.1, limits.inner_top_z + 0.1),
        1e-6,
    )
    assert not upper.isInside(
        cq.Vector(15, limits.front_y - 0.1, limits.inner_top_z + 0.1),
        1e-6,
    )
    assert upper.isInside(
        cq.Vector(15, limits.front_y - 4, limits.inner_top_z + 0.1),
        1e-6,
    )
    assert upper.isInside(
        cq.Vector(15, limits.front_y - 0.1, limits.outer_top_z - 0.1),
        1e-6,
    )

    pawl_pilot = _captured_pawl_pilot(limits)
    assert upper.intersect(pawl_pilot).Volume() == pytest.approx(0, abs=1e-6)
    assert pawl_pilot.BoundingBox().ymax == pytest.approx(
        limits.front_y + 0.05, abs=1e-5
    )

    shaft_support = _captured_shaft_support(limits)
    support_box = shaft_support.BoundingBox()
    assert shaft_support.isValid()
    assert len(shaft_support.Solids()) == 1
    assert support_box.ylen == pytest.approx(2 * enclosure.shaft_support_boss_radius)
    assert support_box.zmin == pytest.approx(-enclosure.shaft_support_boss_radius)
    assert support_box.zmax == pytest.approx(enclosure.shaft_support_boss_radius)
    assert not shaft_support.isInside(
        cq.Vector(DESIGN.drum_outer_width / 2 + 1, 0, 0),
        1e-6,
    )
    assert shaft_support.isInside(
        cq.Vector(DESIGN.drum_outer_width / 2 + 1, 2, 0),
        1e-6,
    )
    shaft_visible_mid_x = (
        limits.inner_x_max
        + DESIGN.drum_outer_width / 2
        + enclosure.shaft_support_axial_clearance
    ) / 2
    assert not shaft_support.isInside(
        cq.Vector(shaft_visible_mid_x, 4.0, 0),
        1e-6,
    )
    assert shaft_support.isInside(
        cq.Vector(limits.inner_x_max - 0.05, 4.4, 0),
        1e-6,
    )
    shaft_boss_end_x = (
        DESIGN.drum_outer_width / 2 + enclosure.shaft_support_axial_clearance
    )
    assert not shaft_support.isInside(
        cq.Vector(shaft_boss_end_x + 0.1, 3.8, 0),
        1e-6,
    )
    assert shaft_support.isInside(
        cq.Vector(
            shaft_boss_end_x + enclosure.boss_end_chamfer + 0.1,
            3.8,
            0,
        ),
        1e-6,
    )
    shaft_head_recess = _captured_shaft_head_recess(limits)
    shaft_head_box = shaft_head_recess.BoundingBox()
    assert shaft_head_recess.isValid()
    assert shaft_head_box.ylen == pytest.approx(
        enclosure.shaft_head_recess_diameter,
        abs=1e-5,
    )
    assert shaft_head_box.zlen == pytest.approx(
        enclosure.shaft_head_recess_diameter,
        abs=1e-5,
    )
    assert shaft_head_box.xlen == pytest.approx(
        enclosure.shaft_head_recess_depth + 0.1,
        abs=1e-5,
    )
    assert lower.intersect(shaft_head_recess).Volume() == pytest.approx(
        0,
        abs=1e-6,
    )

    motor_bosses = _captured_motor_mount_bosses(limits)
    motor_pilots = _captured_motor_mount_pilots(limits)
    assert motor_bosses.isValid()
    assert len(motor_bosses.Solids()) == 2
    assert len(motor_pilots.Solids()) == 2
    assert motor_bosses.cut(motor_pilots).cut(lower).Volume() == pytest.approx(
        0,
        abs=1e-6,
    )
    assert lower.intersect(motor_pilots).Volume() == pytest.approx(0, abs=1e-6)
    assert motor_bosses.BoundingBox().xmax == pytest.approx(
        -DESIGN.drum_outer_width / 2 - enclosure.motor_mount_disc_clearance
    )
    motor_boss_end_x = (
        -DESIGN.drum_outer_width / 2 - enclosure.motor_mount_disc_clearance
    )
    assert not motor_bosses.isInside(
        cq.Vector(
            motor_boss_end_x - 0.1,
            DESIGN.motor.mount_center_offset + 3.8,
            -DESIGN.motor.shaft_offset,
        ),
        1e-6,
    )
    assert motor_bosses.isInside(
        cq.Vector(
            motor_boss_end_x - enclosure.boss_end_chamfer - 0.1,
            DESIGN.motor.mount_center_offset + 3.8,
            -DESIGN.motor.shaft_offset,
        ),
        1e-6,
    )
    motor_visible_mid_x = (
        limits.inner_x_min
        - DESIGN.drum_outer_width / 2
        - enclosure.motor_mount_disc_clearance
    ) / 2
    assert not motor_bosses.isInside(
        cq.Vector(
            motor_visible_mid_x,
            DESIGN.motor.mount_center_offset + 4.0,
            -DESIGN.motor.shaft_offset,
        ),
        1e-6,
    )
    assert motor_bosses.isInside(
        cq.Vector(
            limits.inner_x_min + 0.05,
            DESIGN.motor.mount_center_offset + 4.4,
            -DESIGN.motor.shaft_offset,
        ),
        1e-6,
    )

    alignment_keys = _captured_alignment_frustums(limits, sockets=False)
    alignment_sockets = _captured_alignment_frustums(limits, sockets=True)
    assert alignment_keys.isValid()
    assert alignment_sockets.isValid()
    assert len(alignment_keys.Solids()) == 4
    assert len(alignment_sockets.Solids()) == 4
    assert alignment_keys.cut(lower).Volume() == pytest.approx(0, abs=1e-6)
    assert upper.intersect(alignment_sockets).Volume() == pytest.approx(0, abs=1e-6)
    assert alignment_keys.BoundingBox().zlen == pytest.approx(
        enclosure.alignment_height + 0.1,
        abs=1e-5,
    )

    stack_keys = _captured_stack_alignment_frustums(limits, sockets=False)
    stack_sockets = _captured_stack_alignment_frustums(limits, sockets=True)
    assert stack_keys.isValid()
    assert stack_sockets.isValid()
    assert len(stack_keys.Solids()) == 4
    assert len(stack_sockets.Solids()) == 4
    assert stack_keys.cut(lower).Volume() == pytest.approx(0, abs=1e-6)
    assert upper.intersect(stack_sockets).Volume() == pytest.approx(0, abs=1e-6)
    stacked_keys = stack_keys.translate((0, 0, limits.outer_height))
    assert stacked_keys.cut(stack_sockets).Volume() == pytest.approx(0, abs=1e-6)
    assert stacked_keys.intersect(upper).Volume() == pytest.approx(0, abs=1e-6)
    assert stack_keys.BoundingBox().xmin == pytest.approx(
        limits.outer_x_min + enclosure.capture_outer_corner_radius,
        abs=1e-5,
    )
    assert stack_keys.BoundingBox().xmax == pytest.approx(
        limits.outer_x_max - enclosure.capture_outer_corner_radius,
        abs=1e-5,
    )

    upper_magnets = _captured_magnet_pockets(limits, upper=True)
    lower_magnets = _captured_magnet_pockets(limits, upper=False)
    assert len(upper_magnets.Solids()) == 2
    assert len(lower_magnets.Solids()) == 2
    expected_magnet_radius = (
        enclosure.magnet_diameter / 2 + enclosure.magnet_radial_clearance
    )
    expected_magnet_depth = (
        enclosure.magnet_thickness + enclosure.magnet_depth_clearance + 0.05
    )
    assert upper_magnets.Volume() == pytest.approx(
        2 * math.pi * expected_magnet_radius**2 * expected_magnet_depth,
        rel=1e-6,
    )
    assert upper.intersect(upper_magnets).Volume() == pytest.approx(0, abs=1e-6)
    assert lower.intersect(lower_magnets).Volume() == pytest.approx(0, abs=1e-6)
    for upper_magnet, lower_magnet in zip(
        upper_magnets.Solids(), lower_magnets.Solids(), strict=True
    ):
        assert upper_magnet.Center().x == pytest.approx(lower_magnet.Center().x)
        assert upper_magnet.Center().y == pytest.approx(lower_magnet.Center().y)
        assert upper_magnet.Center().y == pytest.approx(
            (
                limits.back_y
                + enclosure.alignment_end_inset
                + limits.front_y
                - enclosure.alignment_end_inset
            )
            / 2
        )

    top_stack_magnet = _captured_stack_magnet_pocket(limits, top=True)
    bottom_stack_magnet = _captured_stack_magnet_pocket(limits, top=False)
    assert top_stack_magnet.isValid()
    assert bottom_stack_magnet.isValid()
    assert top_stack_magnet.BoundingBox().xlen == pytest.approx(
        2 * expected_magnet_radius
    )
    assert top_stack_magnet.BoundingBox().ylen == pytest.approx(
        2 * expected_magnet_radius
    )
    assert top_stack_magnet.BoundingBox().zlen == pytest.approx(expected_magnet_depth)
    assert top_stack_magnet.Center().x == pytest.approx(0)
    assert bottom_stack_magnet.Center().x == pytest.approx(0)
    assert top_stack_magnet.Center().y == pytest.approx(
        (limits.back_y + limits.front_y) / 2
    )
    assert bottom_stack_magnet.Center().y == pytest.approx(top_stack_magnet.Center().y)
    assert upper.intersect(top_stack_magnet).Volume() == pytest.approx(0, abs=1e-6)
    assert lower.intersect(bottom_stack_magnet).Volume() == pytest.approx(
        0,
        abs=1e-6,
    )

    assert ALPHA_FONT_PATH.is_file()
    alpha = _captured_top_alpha_cutter(limits)
    alpha_box = alpha.BoundingBox()
    assert alpha.isValid()
    assert len(alpha.Solids()) == 2
    assert alpha_box.xlen > 40
    assert alpha_box.ylen > 40
    assert alpha_box.zmin == pytest.approx(
        limits.outer_top_z - enclosure.top_mark_depth,
        abs=1e-5,
    )
    assert alpha_box.zmax == pytest.approx(limits.outer_top_z + 0.05, abs=1e-5)
    assert alpha.Center().x < 0
    assert alpha.Center().y < (limits.back_y + limits.front_y) / 2
    split_probe = (
        cq.Workplane("XY")
        .box(100, enclosure.top_mark_split_gap - 0.1, 2)
        .translate(
            (
                0,
                (limits.back_y + limits.front_y) / 2,
                limits.outer_top_z - 0.5,
            )
        )
        .val()
    )
    assert alpha.intersect(split_probe).Volume() == pytest.approx(0, abs=1e-6)
    assert upper.intersect(alpha).Volume() == pytest.approx(0, abs=1e-6)
    assert alpha.intersect(stack_sockets).Volume() == pytest.approx(0, abs=1e-6)
    assert upper.BoundingBox().ymax == pytest.approx(
        limits.front_y,
        abs=1e-5,
    )

    print_plate, print_layout = _captured_bambu_a1_mini_plate(parts, pawls)
    print_box = print_plate.BoundingBox()
    assert print_plate.isValid()
    assert len(print_plate.Solids()) == 4
    assert print_box.zmin == pytest.approx(0, abs=1e-5)
    assert (print_box.xmin + print_box.xmax) / 2 == pytest.approx(
        A1_MINI_BUILD_VOLUME_MM[0] / 2
    )
    assert (print_box.ymin + print_box.ymax) / 2 == pytest.approx(
        A1_MINI_BUILD_VOLUME_MM[1] / 2
    )
    assert print_box.xmin >= A1_MINI_PLATE_MARGIN_MM
    assert print_box.ymin >= A1_MINI_PLATE_MARGIN_MM
    assert print_box.xmax <= A1_MINI_BUILD_VOLUME_MM[0] - A1_MINI_PLATE_MARGIN_MM
    assert print_box.ymax <= A1_MINI_BUILD_VOLUME_MM[1] - A1_MINI_PLATE_MARGIN_MM
    assert print_box.zmax <= A1_MINI_BUILD_VOLUME_MM[2]
    assert print_layout["enclosure_upper"]["bed_face"] == "front enclosure rim"
    assert print_layout["enclosure_lower"]["bed_face"] == "front enclosure rim"
    assert print_layout["pawl_definitive"]["bed_face"] == "flat rear face"
    assert print_layout["pawl_prototype"]["bed_face"] == "flat rear face"
    assert print_layout["enclosure_upper"]["rotation_deg"] == {"x": -90, "z": 0}


def test_side_recesses_leave_two_millimetres_and_have_45_degree_lead_ins() -> None:
    capture = json.loads(CARD_CAPTURE.read_text(encoding="utf-8"))
    limits = captured_enclosure_limits(capture)
    enclosure = DESIGN.drum_enclosure

    assert (
        limits.inner_x_min - (limits.outer_x_min + enclosure.motor_inset_depth)
    ) == pytest.approx(2)
    assert (
        limits.outer_x_max - enclosure.docking_recess_depth - limits.inner_x_max
    ) == pytest.approx(2)

    motor_pocket = _captured_motor_mount_pocket(limits)
    docking_recess = _captured_docking_recess(limits)
    assert motor_pocket.isValid()
    assert docking_recess.isValid()
    assert motor_pocket.BoundingBox().xmax == pytest.approx(
        limits.outer_x_min + enclosure.motor_inset_depth + 0.05,
        abs=1e-5,
    )
    assert len(motor_pocket.Solids()) == 1
    inner_motor_section = motor_pocket.intersect(
        cq.Workplane("XY")
        .box(0.02, 120, 120)
        .translate(
            (
                limits.outer_x_min + enclosure.motor_inset_depth - 0.01,
                0,
                -30,
            )
        )
        .val()
    )
    rounded_card_margin = (
        enclosure.electronics_card_clearance
        + enclosure.motor_electronics_corner_radius * (1 - 1 / math.sqrt(2))
    )
    assert inner_motor_section.BoundingBox().ylen == pytest.approx(
        enclosure.electronics_card_width + 2 * rounded_card_margin,
        abs=0.05,
    )
    expected_pocket_min_z = min(
        enclosure.electronics_card_center_z
        - enclosure.electronics_card_height / 2
        - rounded_card_margin,
        -DESIGN.motor.shaft_offset
        - DESIGN.motor.backpack_extent
        - enclosure.docking_clearance
        - enclosure.motor_cable_clearance,
    )
    expected_pocket_max_z = max(
        enclosure.electronics_card_center_z
        + enclosure.electronics_card_height / 2
        + rounded_card_margin,
        -DESIGN.motor.shaft_offset
        + DESIGN.motor.chassis_radius
        + enclosure.docking_clearance,
    )
    assert inner_motor_section.BoundingBox().zlen == pytest.approx(
        expected_pocket_max_z - expected_pocket_min_z,
        abs=0.05,
    )
    electronics = _captured_electronics_card_envelope(limits)
    electronics_box = electronics.BoundingBox()
    assert electronics_box.xlen == pytest.approx(enclosure.motor_inset_depth)
    assert electronics_box.ylen == pytest.approx(enclosure.electronics_card_width)
    assert electronics_box.zlen == pytest.approx(enclosure.electronics_card_height)
    assert electronics.cut(motor_pocket).Volume() == pytest.approx(0, abs=1e-6)
    assert docking_recess.BoundingBox().xmin == pytest.approx(
        limits.outer_x_max - enclosure.docking_recess_depth - 0.05,
        abs=1e-5,
    )

    outer_section = docking_recess.intersect(
        cq.Workplane("XY")
        .box(0.02, 60, 60)
        .translate((limits.outer_x_max - 0.01, 0, -DESIGN.motor.shaft_offset))
        .val()
    )
    inner_section = docking_recess.intersect(
        cq.Workplane("XY")
        .box(0.02, 60, 60)
        .translate(
            (
                limits.outer_x_max - enclosure.docking_recess_depth + 0.01,
                0,
                -DESIGN.motor.shaft_offset,
            )
        )
        .val()
    )
    assert (
        outer_section.BoundingBox().ylen - inner_section.BoundingBox().ylen
    ) / 2 == pytest.approx(
        enclosure.side_feature_chamfer,
        abs=0.05,
    )


def test_captured_enclosure_clears_mechanism_and_ignores_floor_solver_outliers() -> (
    None
):
    components = captured_enclosure_design_components(CARD_CAPTURE)
    shapes = {component.name: component.shape for component in components}
    shell = cq.Compound.makeCompound(
        [shapes["enclosure_upper"], shapes["enclosure_lower"]]
    )
    for name in (
        "motor_body",
        "motor_backpack",
        "motor_collar",
        "motor_shaft",
        "electronics_card_envelope",
        "motor_side",
        "shaft_side",
        "support_front",
        "support_back",
    ):
        assert shell.intersect(shapes[name]).Volume() == pytest.approx(0, abs=1e-6)

    capture = json.loads(CARD_CAPTURE.read_text(encoding="utf-8"))
    limits = captured_enclosure_limits(capture)
    assert shapes["motor_body"].BoundingBox().xmax == pytest.approx(
        limits.outer_x_min + DESIGN.drum_enclosure.motor_inset_depth
    )

    intersecting_cards = {
        number
        for number in range(DESIGN.drum.positions)
        if any(
            shapes[half].intersect(shapes[f"card_{number:02d}"]).Volume() > 1e-5
            for half in ("enclosure_upper", "enclosure_lower")
        )
    }
    assert intersecting_cards == set()

    below_floor_cards = {
        number
        for number in range(DESIGN.drum.positions)
        if shapes[f"card_{number:02d}"].BoundingBox().zmin < -75
    }
    assert below_floor_cards == {25, 26, 27, 28}


def test_cq_editor_enclosure_entry_point_builds_exploded_module() -> None:
    namespace = runpy.run_path(str(MECHANICAL_DIR / "view_enclosure.py"))
    result = namespace["result"]
    assert isinstance(result, cq.Assembly)
    assert result.name == "alphabets-v2-captured-enclosure"
    assert result.toCompound().isValid()
    assert {"enclosure_upper", "enclosure_lower"} < set(namespace["objects"])
    assert "pawl_definitive" in namespace["objects"]
    assert "card_00" in namespace["objects"]
    assert "sticker_00_front" in namespace["objects"]
    assert "sticker_00_back" in namespace["objects"]


def test_legacy_holder_and_enclosure_reference_are_preserved() -> None:
    holder = legacy_holder_side()
    assert holder.isValid()
    assert_bounds(holder, (102.5, 40.0, 2.5))
    enclosure = enclosure_reference_edges()
    assert enclosure.BoundingBox().xlen == pytest.approx(100.0)
    assert enclosure.BoundingBox().ylen == pytest.approx(135.0)
    assert len(enclosure.Edges()) == 8


def test_generated_manufacturing_files_are_readable() -> None:
    manifest = json.loads((GENERATED / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["SPDX-FileCopyrightText"] == (
        "2014-2026 The Beach Lab <https://beachlab.org>"
    )
    assert manifest["SPDX-License-Identifier"] == "MIT"
    assert manifest["units"] == "mm"
    assert manifest["parameters"]["drum"]["positions"] == 64
    assert manifest["geometry"]["drum_assembly"]["valid"] is True

    for path in sorted((GENERATED / "cut").glob("*.dxf")):
        document = ezdxf.readfile(path)
        assert len(document.modelspace()) > 0, path.name
        text = path.read_text(encoding="utf-8")
        assert "{00000000-0000-0000-0000-000000000001}" in text
        assert "1970-01-01T00:00:00+00:00" in text

    card_dxf = ezdxf.readfile(GENERATED / "cut/flap-card.dxf")
    actual_edges = {
        tuple(
            sorted(
                (
                    (round(entity.dxf.start.x, 6), round(entity.dxf.start.y, 6)),
                    (round(entity.dxf.end.x, 6), round(entity.dxf.end.y, 6)),
                )
            )
        )
        for entity in card_dxf.modelspace().query("LINE")
    }
    points = card_points()
    expected_edges = {
        tuple(sorted((points[index], points[(index + 1) % len(points)])))
        for index in range(len(points))
    }
    assert actual_edges == expected_edges

    for path in sorted((GENERATED / "step").glob("*.step")):
        shape = cq.importers.importStep(str(path)).val()
        assert shape.isValid(), path.name
        assert shape.BoundingBox().DiagonalLength > 0
        assert "'1970-01-01T00:00:00'" in path.read_text(encoding="utf-8")

    for path in sorted((GENERATED / "print").glob("*.stl")):
        assert path.stat().st_size > 1000, path.name

    preview = GENERATED / "preview/module-reference.svg"
    assert preview.stat().st_size > 1000
    assert "<svg" in preview.read_text(encoding="utf-8")
    motor_preview = GENERATED / "preview/motor-28byj48-reference.svg"
    assert motor_preview.stat().st_size > 1000
    assert "<svg" in motor_preview.read_text(encoding="utf-8")


def test_parallel_stale_enclosure_exports_are_absent() -> None:
    stale_paths = (
        GENERATED / "preview/enclosure-exploded.svg",
        GENERATED / "preview/enclosure-module.svg",
        GENERATED / "print/drum-enclosure-lower.stl",
        GENERATED / "print/drum-enclosure-upper.stl",
        GENERATED / "step/drum-enclosure-assembly.step",
        GENERATED / "step/drum-enclosure-lower.step",
        GENERATED / "step/drum-enclosure-upper.step",
        GENERATED / "step/enclosed-module-reference.step",
    )
    assert not any(path.exists() for path in stale_paths)
    assert (
        GENERATED
        / "captured-enclosure/print/captured-enclosure-bambu-a1-mini-four-part-plate.stl"
    ).exists()


def test_captured_enclosure_manufacturing_files_are_readable() -> None:
    output = GENERATED / "captured-enclosure"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["capture"]["frame"] == 27464
    assert manifest["capture"]["controller"]["display_position"] == 37
    assert manifest["limits_mm"]["inner_bottom_z"] == pytest.approx(-75, abs=1e-5)
    assert manifest["geometry"]["enclosure_upper"]["solid_count"] == 1
    assert manifest["geometry"]["enclosure_lower"]["solid_count"] == 1
    assert manifest["geometry"]["pawl_definitive"]["solid_count"] == 1
    assert manifest["geometry"]["pawl_prototype"]["solid_count"] == 1
    assert manifest["parameters"]["top_mark_depth"] == pytest.approx(0.2)
    assert manifest["parameters"]["top_mark_rotation"] == pytest.approx(180)
    assert manifest["parameters"]["electronics_card_width"] == pytest.approx(50)
    assert manifest["parameters"]["electronics_card_height"] == pytest.approx(35)
    assert manifest["parameters"]["magnet_diameter"] == pytest.approx(3)
    assert manifest["parameters"]["magnet_thickness"] == pytest.approx(1)
    assert manifest["parameters"]["magnet_radial_clearance"] == pytest.approx(0.2)
    assert manifest["parameters"]["magnet_depth_clearance"] == pytest.approx(0.2)
    assert manifest["parameters"]["pawl_head_recess_diameter"] == pytest.approx(6)
    assert manifest["parameters"]["pawl_head_recess_depth"] == pytest.approx(1)
    assert manifest["parameters"]["shaft_head_recess_diameter"] == pytest.approx(6)
    assert manifest["parameters"]["shaft_head_recess_depth"] == pytest.approx(2)
    assert "alpha top face" in manifest["features"]["vertical_stack_magnets"]
    assert manifest["print_plate"]["printer"] == "Bambu Lab A1 mini"
    assert manifest["print_plate"]["build_volume_mm"] == [180, 180, 180]
    assert manifest["print_plate"]["geometry"]["solid_count"] == 4

    expected_step = {
        "captured-enclosure-upper.step",
        "captured-enclosure-lower.step",
        "captured-enclosure-assembly.step",
        "captured-enclosure-pawl-definitive.step",
        "captured-enclosure-pawl-prototype.step",
    }
    assert {path.name for path in (output / "step").glob("*.step")} == expected_step
    for path in sorted((output / "step").glob("*.step")):
        shape = cq.importers.importStep(str(path)).val()
        assert shape.isValid(), path.name
        assert shape.BoundingBox().DiagonalLength > 0

    expected_stl = {
        "captured-enclosure-bambu-a1-mini-four-part-plate.stl",
        "captured-enclosure-upper.stl",
        "captured-enclosure-lower.stl",
        "captured-enclosure-pawl-definitive.stl",
        "captured-enclosure-pawl-prototype.stl",
    }
    assert {path.name for path in (output / "print").glob("*.stl")} == expected_stl
    for path in sorted((output / "print").glob("*.stl")):
        assert path.stat().st_size > 1000, path.name

    preview = (output / "preview/captured-enclosure-module.svg").read_text(
        encoding="utf-8"
    )
    hidden_lines = preview.split("<!-- hidden lines -->", 1)[1].split(
        "<!-- solid lines -->", 1
    )[0]
    assert "<path" not in hidden_lines
