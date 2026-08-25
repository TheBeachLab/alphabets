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
    _captured_hole_center,
    captured_card_components,
    captured_enclosure_design_components,
    captured_enclosure_view_groups,
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
    _captured_electronics_card_envelope,
    _captured_motor_mount_bosses,
    _captured_motor_mount_pilots,
    _captured_pawl_mount,
    _captured_pawl_pilot,
    _captured_pawl_screw_axis_z,
    _captured_shaft_head_recess,
    _captured_shaft_support,
    _captured_side_pockets,
    _captured_stack_alignment_frustums,
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
PROTOTYPE_DIR = MECHANICAL_DIR.parent
HARDWARE_DIR = PROTOTYPE_DIR.parent
FINAL_DIR = HARDWARE_DIR / "Final"
REPO_ROOT = HARDWARE_DIR.parents[1]
GENERATED = MECHANICAL_DIR / "generated"
CARD_CAPTURE = MECHANICAL_DIR / "reference/cards-position-capture-final.json"


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
    catalog = json.loads(
        (HARDWARE_DIR / "variants/variants.json").read_text(encoding="utf-8")
    )
    prototype = next(item for item in catalog["variants"] if item["id"] == "prototype")
    assert prototype["character_preset"] == "demo-64"
    assert prototype["card_mm"]["body_width"] == DESIGN.card.body_width
    assert prototype["card_mm"]["total_height"] == DESIGN.card.total_height
    assert prototype["card_mm"]["tab_height"] == DESIGN.card.tab_height
    assert prototype["sticker_mm"]["width"] == DESIGN.card.sticker_width
    assert prototype["sticker_mm"]["split_y"] == DESIGN.card.sticker_face_height
    assert prototype["drum_mm"]["inner_width"] == DESIGN.drum_inner_width
    assert prototype["drum_mm"]["outer_width"] == DESIGN.drum_outer_width

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

    capture = json.loads(CARD_CAPTURE.read_text(encoding="utf-8"))
    assert capture["capture_frame"] == 27464
    assert capture["source_blend"].startswith("V2/Hardware/Final/")


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
    assert DESIGN.card.tab_start_height == pytest.approx(40.0)
    assert DESIGN.card.tab_axis_height == pytest.approx(41.5)
    assert DESIGN.card.tab_rotation_radius == pytest.approx(math.sqrt(1.5**2 + 0.25**2))
    assert DESIGN.card.finished_thickness == pytest.approx(0.7)
    assert DESIGN.card.sticker_side_margin == pytest.approx(2.5)
    assert DESIGN.card.sticker_y_offset == pytest.approx(DESIGN.card.tab_height)
    assert DESIGN.drum.allow_tab_interference is True
    assert DESIGN.flap_tab_radial_clearance == pytest.approx(-0.0206906326)


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
    assert card.isInside(cq.Vector(25, 42, -0.05), 1e-6)
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
    assert params.drum_enclosure.side_clearance == 2.5
    assert params.drum_inner_width == pytest.approx(56.5)
    assert params.enclosure_inner_height == pytest.approx(DESIGN.enclosure_inner_height)
    assert params.enclosure_inner_width == pytest.approx(65.8)
    assert params.enclosure_outer_width == pytest.approx(
        params.enclosure_inner_width + 2 * params.drum_enclosure.wall_thickness
    )


def test_design_profile_rejects_unknown_dimension(tmp_path: Path) -> None:
    profile = tmp_path / "invalid.toml"
    profile.write_text("[drum]\nunknown_dimension = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown_dimension"):
        load_design_profile(profile, base=DESIGN)


def test_design_profile_rejects_a_tab_that_cannot_rotate(tmp_path: Path) -> None:
    profile = tmp_path / "blocked-tab.toml"
    profile.write_text("[drum]\nallow_tab_interference = false\n", encoding="utf-8")
    with pytest.raises(ValueError, match="required radial clearance"):
        load_design_profile(profile, base=DESIGN)


def test_enclosure_primary_controls_are_direct_and_safe(tmp_path: Path) -> None:
    profile = tmp_path / "enclosure.toml"
    profile.write_text(
        """[drum_enclosure]
top_distance = 70.0
bottom_distance = 72.0
back_distance = 65.0
side_clearance = 3.0
wall_thickness = 10.0
side_inset_depth = 7.0
""",
        encoding="utf-8",
    )
    params = load_design_profile(profile, base=DESIGN)
    enclosure = params.drum_enclosure
    assert enclosure.front_chamfer == pytest.approx(5)
    assert enclosure.remaining_side_wall == pytest.approx(3)
    capture = json.loads(CARD_CAPTURE.read_text(encoding="utf-8"))
    baseline = captured_enclosure_limits(capture)
    limits = captured_enclosure_limits(capture, params)
    assert limits.inner_top_z == pytest.approx(70)
    assert limits.inner_bottom_z == pytest.approx(-72)
    assert limits.back_y == pytest.approx(-65)
    assert limits.front_y == pytest.approx(baseline.front_y)
    assert limits.inner_x_min == pytest.approx(-params.drum_outer_width / 2 - 3)
    assert limits.inner_x_max == pytest.approx(params.drum_outer_width / 2 + 3)


def test_enclosure_rejects_an_inset_that_removes_the_wall(tmp_path: Path) -> None:
    profile = tmp_path / "invalid-enclosure.toml"
    profile.write_text(
        "[drum_enclosure]\nwall_thickness = 6.0\nside_inset_depth = 6.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="smaller than wall_thickness"):
        load_design_profile(profile, base=DESIGN)


def test_zero_disables_every_configurable_enclosure_chamfer(tmp_path: Path) -> None:
    profile = tmp_path / "zero-chamfers.toml"
    profile.write_text(
        """[drum_enclosure]
side_pocket_chamfer = 0.0
boss_end_chamfer = 0.0
top_mark_chamfer = 0.0
pawl_outer_chamfer = 0.0
""",
        encoding="utf-8",
    )
    params = load_design_profile(profile, base=DESIGN)
    capture = json.loads(CARD_CAPTURE.read_text(encoding="utf-8"))

    enclosure_parts = captured_drum_enclosure_parts(capture, params)
    pawl_parts = captured_pawl_parts(capture, params)

    assert all(part.isValid() for part in enclosure_parts.values())
    assert all(part.isValid() for part in pawl_parts.values())


@pytest.mark.parametrize(
    "name",
    (
        "side_pocket_chamfer",
        "boss_end_chamfer",
        "top_mark_chamfer",
        "pawl_outer_chamfer",
    ),
)
def test_enclosure_rejects_negative_chamfers(tmp_path: Path, name: str) -> None:
    profile = tmp_path / f"negative-{name}.toml"
    profile.write_text(
        f"[drum_enclosure]\n{name} = -0.1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=f"{name} cannot be negative"):
        load_design_profile(profile, base=DESIGN)


@pytest.mark.parametrize(
    "name",
    ("side_pocket_margin", "side_pocket_corner_radius"),
)
def test_enclosure_rejects_negative_side_pocket_dimensions(
    tmp_path: Path,
    name: str,
) -> None:
    profile = tmp_path / f"negative-{name}.toml"
    profile.write_text(
        f"[drum_enclosure]\n{name} = -0.1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=f"{name} cannot be negative"):
        load_design_profile(profile, base=DESIGN)


def test_side_pocket_radius_covers_its_chamfer(tmp_path: Path) -> None:
    profile = tmp_path / "small-side-pocket-radius.toml"
    profile.write_text(
        """[drum_enclosure]
side_inset_depth = 4.0
side_pocket_chamfer = 4.0
side_pocket_corner_radius = 3.0
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="at least the side pocket chamfer"):
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

    card_volume = flap_card().Volume()
    sticker_volume = (
        DESIGN.card.sticker_width
        * DESIGN.card.sticker_face_height
        * DESIGN.card.sticker_face_thickness
    )
    assert all(
        shapes[f"card_{number:02d}"].Volume() == pytest.approx(card_volume)
        for number in range(64)
    )
    assert all(
        shapes[f"sticker_{number:02d}_{face}"].Volume() == pytest.approx(sticker_volume)
        for number in range(64)
        for face in ("front", "back")
    )


def test_every_captured_tab_axis_is_centred_in_its_rotated_drum_hole() -> None:
    data = json.loads(CARD_CAPTURE.read_text(encoding="utf-8"))
    components = captured_card_components(CARD_CAPTURE)
    cards = {
        component.name: component.shape
        for component in components
        if component.name.startswith("card_")
    }
    capture_rotation = float(data["controller"]["rotation_x_degrees"])
    tab_center_x = DESIGN.card.body_width / 2 + DESIGN.card.tab_width / 2

    for number in range(DESIGN.drum.positions):
        hole_center = _captured_hole_center(number, capture_rotation)
        card = cards[f"card_{number:02d}"]
        tab_centres = []
        for x in (-tab_center_x, tab_center_x):
            tab_section = card.intersect(
                cq.Workplane("XY")
                .box(0.2, 5, 5)
                .translate((x, hole_center[1], hole_center[2]))
                .val()
            )
            assert tab_section.Volume() > 0, f"card_{number:02d} tab misses its hole"
            tab_centres.append(tab_section.Center())

        for tab_center in tab_centres:
            assert tab_center.y == pytest.approx(hole_center[1], abs=1e-6)
            assert tab_center.z == pytest.approx(hole_center[2], abs=1e-6)
        assert tab_centres[0].y == pytest.approx(tab_centres[1].y, abs=1e-6)
        assert tab_centres[0].z == pytest.approx(tab_centres[1].z, abs=1e-6)


def test_capture_design_view_groups_fit_data_without_floor_or_pawl_solids() -> None:
    components = captured_enclosure_design_components(CARD_CAPTURE)
    names = {component.name for component in components}
    assert {
        "enclosure",
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


def test_capture_view_groups_do_not_duplicate_drum_side_in_motor() -> None:
    components = captured_enclosure_design_components(CARD_CAPTURE)
    groups = captured_enclosure_view_groups(components)
    names_by_group = {
        group: {component.name for component in members}
        for group, members in groups.items()
    }

    assert names_by_group["motor"] == {
        "motor_body",
        "motor_collar",
        "motor_backpack",
        "motor_shaft",
    }
    assert "motor_side" in names_by_group["tambor"]
    assert "motor_side" not in names_by_group["motor"]

    all_grouped_names = [
        component.name for members in groups.values() for component in members
    ]
    assert len(all_grouped_names) == len(set(all_grouped_names))


def test_captured_enclosure_is_open_ended_tube_with_replaceable_pawls() -> None:
    capture = json.loads(CARD_CAPTURE.read_text(encoding="utf-8"))
    limits = captured_enclosure_limits(capture)
    parts = captured_drum_enclosure_parts(capture)
    assert tuple(parts) == ("enclosure",)
    assert all(shape.isValid() for shape in parts.values())
    assert all(len(shape.Solids()) == 1 for shape in parts.values())

    enclosure = DESIGN.drum_enclosure
    assert limits.back_y == pytest.approx(-enclosure.back_distance)
    assert limits.front_y == pytest.approx(40.301814675)
    assert limits.inner_top_z == pytest.approx(enclosure.top_distance)
    assert limits.inner_bottom_z == pytest.approx(-enclosure.bottom_distance)
    assert limits.inner_x_min == pytest.approx(
        -DESIGN.drum_outer_width / 2 - enclosure.side_clearance
    )
    assert limits.inner_x_max == pytest.approx(
        DESIGN.drum_outer_width / 2 + enclosure.side_clearance
    )
    assert limits.outer_width == pytest.approx(
        DESIGN.drum_outer_width
        + 2 * (enclosure.side_clearance + enclosure.wall_thickness)
    )
    assert limits.outer_depth == pytest.approx(limits.front_y + enclosure.back_distance)
    assert limits.outer_height == pytest.approx(
        enclosure.top_distance
        + enclosure.bottom_distance
        + 2 * enclosure.wall_thickness
    )
    assert enclosure.front_chamfer == pytest.approx(enclosure.wall_thickness / 2)

    shell = parts["enclosure"]
    assert shell.BoundingBox().xlen == pytest.approx(limits.outer_width)
    assert shell.BoundingBox().zmin == pytest.approx(
        limits.outer_bottom_z - enclosure.alignment_height,
        abs=1e-5,
    )
    assert shell.BoundingBox().zmax == pytest.approx(limits.outer_top_z, abs=1e-5)

    # The former split plane is continuous enclosure wall, without a seam,
    # alignment keys or magnet pockets. The full side trays retain their
    # configured structural rim at both sides.
    for x in (
        (limits.outer_x_min + limits.inner_x_min) / 2,
        (limits.outer_x_max + limits.inner_x_max) / 2,
    ):
        assert shell.isInside(
            cq.Vector(
                x,
                limits.back_y + enclosure.side_pocket_margin / 2,
                12.0,
            ),
            1e-6,
        )
    center_y = (limits.back_y + limits.front_y) / 2
    assert shell.isInside(cq.Vector(0, center_y, limits.outer_top_z - 0.1), 1e-6)
    assert shell.isInside(cq.Vector(0, center_y, limits.outer_bottom_z + 0.1), 1e-6)

    for end_y in (limits.back_y, limits.front_y):
        opening_probe = (
            cq.Workplane("XY").box(20, 1, 80).translate((15, end_y, 0)).val()
        )
        assert shell.intersect(opening_probe).Volume() == pytest.approx(0)

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
    assert shell.intersect(pawl).Volume() == pytest.approx(0)
    assert pawl.isInside(
        cq.Vector(4.8, limits.front_y + 0.5, _captured_pawl_screw_axis_z(limits)),
        1e-6,
    )
    outer_edge_probe = cq.Vector(
        4.8,
        pawl_box.ymax - 0.1,
        _captured_pawl_screw_axis_z(limits),
    )
    assert pawl.isInside(outer_edge_probe, 1e-6) is (enclosure.pawl_outer_chamfer == 0)
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
    assert shell.isInside(
        cq.Vector(6, limits.front_y - 0.1, limits.inner_top_z + 0.1),
        1e-6,
    )
    assert not shell.isInside(
        cq.Vector(15, limits.front_y - 0.1, limits.inner_top_z + 0.1),
        1e-6,
    )
    assert shell.isInside(
        cq.Vector(15, limits.front_y - 4, limits.inner_top_z + 0.1),
        1e-6,
    )
    assert shell.isInside(
        cq.Vector(15, limits.front_y - 0.1, limits.outer_top_z - 0.1),
        1e-6,
    )

    pawl_pilot = _captured_pawl_pilot(limits)
    assert shell.intersect(pawl_pilot).Volume() == pytest.approx(0, abs=1e-6)
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
    assert shell.intersect(shaft_head_recess).Volume() == pytest.approx(
        0,
        abs=1e-6,
    )

    motor_bosses = _captured_motor_mount_bosses(limits)
    motor_pilots = _captured_motor_mount_pilots(limits)
    assert motor_bosses.isValid()
    assert len(motor_bosses.Solids()) == 2
    assert len(motor_pilots.Solids()) == 2
    assert motor_bosses.cut(motor_pilots).cut(shell).Volume() == pytest.approx(
        0,
        abs=1e-6,
    )
    assert shell.intersect(motor_pilots).Volume() == pytest.approx(0, abs=1e-6)
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

    stack_keys = _captured_stack_alignment_frustums(limits, sockets=False)
    stack_sockets = _captured_stack_alignment_frustums(limits, sockets=True)
    assert stack_keys.isValid()
    assert stack_sockets.isValid()
    assert len(stack_keys.Solids()) == 4
    assert len(stack_sockets.Solids()) == 4
    assert stack_keys.cut(shell).Volume() == pytest.approx(0, abs=1e-6)
    assert shell.intersect(stack_sockets).Volume() == pytest.approx(0, abs=1e-6)
    stacked_keys = stack_keys.translate((0, 0, limits.outer_height))
    assert stacked_keys.cut(stack_sockets).Volume() == pytest.approx(0, abs=1e-6)
    assert stacked_keys.intersect(shell).Volume() == pytest.approx(0, abs=1e-6)
    assert stack_keys.BoundingBox().xmin == pytest.approx(
        limits.outer_x_min + enclosure.capture_outer_corner_radius,
        abs=1e-5,
    )
    assert stack_keys.BoundingBox().xmax == pytest.approx(
        limits.outer_x_max - enclosure.capture_outer_corner_radius,
        abs=1e-5,
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
    assert shell.intersect(alpha).Volume() == pytest.approx(0, abs=1e-6)
    assert alpha.intersect(stack_sockets).Volume() == pytest.approx(0, abs=1e-6)
    assert shell.BoundingBox().ymax == pytest.approx(
        limits.front_y,
        abs=1e-5,
    )

    print_plate, print_layout = _captured_bambu_a1_mini_plate(parts, pawls)
    print_box = print_plate.BoundingBox()
    assert print_plate.isValid()
    assert len(print_plate.Solids()) == 2
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
    assert print_layout["enclosure"]["bed_face"] == "front enclosure rim"
    assert print_layout["pawl_prototype"]["bed_face"] == "flat rear face"
    assert print_layout["enclosure"]["rotation_deg"] == {"x": -90, "z": 0}


def test_one_side_inset_controls_both_full_side_pockets_and_remaining_wall() -> None:
    capture = json.loads(CARD_CAPTURE.read_text(encoding="utf-8"))
    limits = captured_enclosure_limits(capture)
    enclosure = DESIGN.drum_enclosure

    assert (
        limits.inner_x_min - (limits.outer_x_min + enclosure.side_inset_depth)
    ) == pytest.approx(enclosure.remaining_side_wall)
    assert (
        limits.outer_x_max - enclosure.side_inset_depth - limits.inner_x_max
    ) == pytest.approx(enclosure.remaining_side_wall)

    motor_pocket, shaft_pocket = _captured_side_pockets(limits)
    assert motor_pocket.isValid()
    assert shaft_pocket.isValid()
    assert motor_pocket.BoundingBox().xmax == pytest.approx(
        limits.outer_x_min + enclosure.side_inset_depth + 0.05,
        abs=1e-5,
    )
    assert shaft_pocket.BoundingBox().xmin == pytest.approx(
        limits.outer_x_max - enclosure.side_inset_depth - 0.05,
        abs=1e-5,
    )
    assert len(motor_pocket.Solids()) == 1
    assert len(shaft_pocket.Solids()) == 1

    chamfer = min(enclosure.side_pocket_chamfer, enclosure.side_inset_depth)
    expected_width = limits.outer_depth - 2 * enclosure.side_pocket_margin - 2 * chamfer
    expected_height = (
        limits.outer_height - 2 * enclosure.side_pocket_margin - 2 * chamfer
    )
    inner_sections = (
        motor_pocket.intersect(
            cq.Workplane("XY")
            .box(0.02, 200, 200)
            .translate(
                (
                    limits.outer_x_min + enclosure.side_inset_depth - 0.01,
                    0,
                    0,
                )
            )
            .val()
        ),
        shaft_pocket.intersect(
            cq.Workplane("XY")
            .box(0.02, 200, 200)
            .translate(
                (
                    limits.outer_x_max - enclosure.side_inset_depth + 0.01,
                    0,
                    0,
                )
            )
            .val()
        ),
    )
    for section in inner_sections:
        assert section.BoundingBox().ylen == pytest.approx(expected_width, abs=0.05)
        assert section.BoundingBox().zlen == pytest.approx(expected_height, abs=0.05)

    electronics = _captured_electronics_card_envelope(limits)
    electronics_box = electronics.BoundingBox()
    assert electronics_box.xlen == pytest.approx(enclosure.side_inset_depth)
    assert electronics_box.ylen == pytest.approx(enclosure.electronics_card_width)
    assert electronics_box.zlen == pytest.approx(enclosure.electronics_card_height)
    assert electronics.cut(motor_pocket).Volume() == pytest.approx(0, abs=1e-6)
    assert shaft_pocket.Volume() == pytest.approx(motor_pocket.Volume())


def test_captured_enclosure_clears_mechanism_and_ignores_floor_solver_outliers() -> (
    None
):
    components = captured_enclosure_design_components(CARD_CAPTURE)
    shapes = {component.name: component.shape for component in components}
    shell = shapes["enclosure"]
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
        limits.outer_x_min + DESIGN.drum_enclosure.side_inset_depth
    )

    intersecting_cards = {
        number
        for number in range(DESIGN.drum.positions)
        if shell.intersect(shapes[f"card_{number:02d}"]).Volume() > 1e-5
    }
    assert intersecting_cards == set()

    below_floor_cards = {
        number
        for number in range(DESIGN.drum.positions)
        if shapes[f"card_{number:02d}"].BoundingBox().zmin < -75
    }
    # The shorter 43 mm Prototype cards stay above the conservative floor
    # inherited from the trusted Final capture.
    assert below_floor_cards == set()


def test_cq_editor_enclosure_entry_point_builds_exploded_module() -> None:
    namespace = runpy.run_path(str(MECHANICAL_DIR / "view_enclosure.py"))
    result = namespace["result"]
    assert isinstance(result, cq.Assembly)
    assert result.name == "alphabets-v2-captured-enclosure"
    assert result.toCompound().isValid()
    assert "enclosure" in namespace["objects"]
    assert "pawl_prototype" in namespace["objects"]
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
        GENERATED / "cut/enclosure-sketch-reference.dxf",
        GENERATED / "cut/legacy-holder-side.dxf",
    )
    assert not any(path.exists() for path in stale_paths)
    assert (
        GENERATED
        / "captured-enclosure/print/captured-enclosure-bambu-a1-mini-prototype-plate.stl"
    ).exists()


def test_captured_enclosure_manufacturing_files_are_readable() -> None:
    output = GENERATED / "captured-enclosure"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    enclosure = DESIGN.drum_enclosure
    assert manifest["capture"]["frame"] == 27464
    assert manifest["capture"]["controller"]["display_position"] == 37
    assert manifest["limits_mm"]["inner_bottom_z"] == pytest.approx(
        -enclosure.bottom_distance,
        abs=1e-5,
    )
    assert manifest["geometry"]["enclosure"]["solid_count"] == 1
    assert manifest["geometry"]["pawl_prototype"]["solid_count"] == 1
    assert manifest["parameters"]["top_mark_depth"] == pytest.approx(
        enclosure.top_mark_depth
    )
    assert manifest["parameters"]["top_mark_rotation"] == pytest.approx(
        enclosure.top_mark_rotation
    )
    assert manifest["parameters"]["electronics_card_width"] == pytest.approx(
        enclosure.electronics_card_width
    )
    assert manifest["parameters"]["electronics_card_height"] == pytest.approx(
        enclosure.electronics_card_height
    )
    for name in (
        "top_distance",
        "bottom_distance",
        "back_distance",
        "side_clearance",
        "wall_thickness",
        "side_inset_depth",
        "remaining_side_wall",
        "front_chamfer",
        "side_pocket_margin",
        "side_pocket_corner_radius",
    ):
        assert manifest["parameters"][name] == pytest.approx(getattr(enclosure, name))
    assert "motor_electronics_corner_radius" not in manifest["parameters"]
    assert "electronics_card_clearance" not in manifest["parameters"]
    assert "motor_cable_clearance" not in manifest["parameters"]
    assert not any("magnet" in name for name in manifest["parameters"])
    assert "capture_split_height" not in manifest["parameters"]
    assert "split_gap" not in manifest["parameters"]
    assert manifest["parameters"]["pawl_head_recess_diameter"] == pytest.approx(
        enclosure.pawl_head_recess_diameter
    )
    assert manifest["parameters"]["pawl_head_recess_depth"] == pytest.approx(
        enclosure.pawl_head_recess_depth
    )
    assert manifest["parameters"]["shaft_head_recess_diameter"] == pytest.approx(
        enclosure.shaft_head_recess_diameter
    )
    assert manifest["parameters"]["shaft_head_recess_depth"] == pytest.approx(
        enclosure.shaft_head_recess_depth
    )
    assert "vertical_stack_magnets" not in manifest["features"]
    assert manifest["print_plate"]["printer"] == "Bambu Lab A1 mini"
    assert manifest["print_plate"]["build_volume_mm"] == [180, 180, 180]
    assert manifest["physical_variant"] == "prototype"
    assert manifest["character_set"] == "demo-64"
    assert manifest["features"]["visible_assembly_pawl"] == "prototype"
    assert (
        "matching motor-side and shaft-side"
        in manifest["features"]["full_side_pockets"]
    )
    assert "motor_electronics_pocket" not in manifest["features"]
    assert "without an assembly seam" in manifest["features"]["enclosure_construction"]
    assert "split_magnets" not in manifest["features"]
    assert "part_alignment" not in manifest["features"]
    assert manifest["print_plate"]["geometry"]["solid_count"] == 2

    expected_step = {
        "captured-enclosure.step",
        "captured-enclosure-assembly.step",
        "captured-enclosure-pawl-prototype.step",
    }
    assert {path.name for path in (output / "step").glob("*.step")} == expected_step
    for path in sorted((output / "step").glob("*.step")):
        shape = cq.importers.importStep(str(path)).val()
        assert shape.isValid(), path.name
        assert shape.BoundingBox().DiagonalLength > 0

    expected_stl = {
        "captured-enclosure-bambu-a1-mini-prototype-plate.stl",
        "captured-enclosure.stl",
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
