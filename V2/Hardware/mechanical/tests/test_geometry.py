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
    _orient_for_enclosure,
    drum_component_shapes,
    drum_stop_rotation_degrees,
    enclosed_module_assembly,
    enclosed_module_components,
    enclosure_assembly,
    module_reference_assembly,
    module_reference_components,
    mounted_card_components,
)
from alphabets_cad.parameters import DESIGN, load_design_profile
from alphabets_cad.parts import (
    card_points,
    drum_enclosure_parts,
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
HARDWARE_DIR = MECHANICAL_DIR.parent
REPO_ROOT = MECHANICAL_DIR.parents[2]
GENERATED = MECHANICAL_DIR / "generated"


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
    spool = (HARDWARE_DIR / "structure/spool.scad").read_text(encoding="utf-8")
    for name, value in {
        "ncards": DESIGN.drum.positions,
        "sdiam": DESIGN.drum.diameter,
        "e": DESIGN.drum.side_thickness,
        "kerf": DESIGN.drum.laser_kerf,
        "flap_width": DESIGN.card.body_width,
        "axial_clearance": DESIGN.drum.axial_clearance,
        "w": DESIGN.drum.support_width,
        "tabw": DESIGN.drum.support_tab_width,
    }.items():
        match = re.search(rf"(?m)^\s*{name}\s*=\s*([0-9.]+)\s*;", spool)
        assert match, name
        assert float(match.group(1)) == pytest.approx(float(value))

    card_manifest = json.loads(
        (HARDWARE_DIR / "cards/card-50x48.json").read_text(encoding="utf-8")
    )
    assert card_manifest["card_mm"]["body_width"] == DESIGN.card.body_width
    assert card_manifest["card_mm"]["total_height"] == DESIGN.card.total_height
    assert card_manifest["drum_mm"]["inner_width"] == DESIGN.drum_inner_width

    printed_spool = (HARDWARE_DIR / "structure/spool-3dp.scad").read_text(
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

    motor = (HARDWARE_DIR / "structure/28byj48.scad").read_text(encoding="utf-8")
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
        (HARDWARE_DIR / "blender/generated/card-envelope.json").read_text(
            encoding="utf-8"
        )
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


def test_two_part_enclosure_is_valid_separate_and_rear_open() -> None:
    parts = drum_enclosure_parts()
    assert tuple(parts) == ("enclosure_upper", "enclosure_lower")
    assert all(shape.isValid() for shape in parts.values())
    assert all(len(shape.Solids()) == 1 for shape in parts.values())

    enclosure = DESIGN.drum_enclosure
    upper_box = parts["enclosure_upper"].BoundingBox()
    lower_box = parts["enclosure_lower"].BoundingBox()
    assert upper_box.xlen == pytest.approx(DESIGN.enclosure_overall_width)
    assert lower_box.xlen == pytest.approx(DESIGN.enclosure_overall_width)
    assert DESIGN.enclosure_overall_width == pytest.approx(DESIGN.enclosure_outer_width)
    assert upper_box.ylen == pytest.approx(DESIGN.enclosure_outer_depth)
    assert lower_box.ylen == pytest.approx(DESIGN.enclosure_outer_depth)
    assert upper_box.zmin == pytest.approx(enclosure.split_gap / 2)
    assert lower_box.zmax == pytest.approx(-enclosure.split_gap / 2)
    assert upper_box.zmax == pytest.approx(DESIGN.enclosure_outer_height / 2)
    assert lower_box.zmin == pytest.approx(-DESIGN.enclosure_outer_height / 2)
    assert upper_box.zmax == pytest.approx(-lower_box.zmin)
    assert DESIGN.enclosure_ceiling_z == pytest.approx(96.702228)
    assert DESIGN.enclosure_floor_z == pytest.approx(-96.702228)
    assert enclosure.card_ceiling_clearance == pytest.approx(10.0)
    assert enclosure.closure_method == "embedded_magnets"
    assert parts["enclosure_upper"].intersect(
        parts["enclosure_lower"]
    ).Volume() == pytest.approx(0)

    rear_opening_probe = (
        cq.Workplane(
            "XY",
            origin=(0, DESIGN.enclosure_inner_depth / 2, 0),
        )
        .box(
            DESIGN.enclosure_inner_width - 2,
            1,
            DESIGN.enclosure_inner_height - 2,
        )
        .val()
    )
    for shape in parts.values():
        assert shape.intersect(rear_opening_probe).Volume() == pytest.approx(0)


def test_enclosure_roof_respects_captured_card_envelope_and_clearance() -> None:
    parts = drum_enclosure_parts()
    enclosure = DESIGN.drum_enclosure
    upper = parts["enclosure_upper"]
    lower = parts["enclosure_lower"]

    assert DESIGN.upper_card_protrusion_above_drum == pytest.approx(44.202228)
    assert DESIGN.enclosure_ceiling_z - enclosure.upper_card_envelope_height == (
        pytest.approx(enclosure.card_ceiling_clearance)
    )

    cavity_probe = (
        cq.Workplane(
            "XY",
            origin=(0, 0, DESIGN.enclosure_ceiling_z - 0.5),
        )
        .box(1, 1, 0.5)
        .val()
    )
    upper_roof_probe = (
        cq.Workplane(
            "XY",
            origin=(
                0,
                0,
                DESIGN.enclosure_ceiling_z + enclosure.wall_thickness / 2,
            ),
        )
        .box(1, 1, enclosure.wall_thickness / 2)
        .val()
    )
    lower_floor_probe = upper_roof_probe.mirror("XY")
    assert upper.intersect(cavity_probe).Volume() == pytest.approx(0)
    assert upper.intersect(upper_roof_probe).Volume() > 0
    assert lower.intersect(lower_floor_probe).Volume() > 0


def test_enclosure_window_and_drum_clearances_are_real_geometry() -> None:
    parts = drum_enclosure_parts()
    shell = cq.Compound.makeCompound(list(parts.values()))
    enclosure = DESIGN.drum_enclosure
    front_y = -DESIGN.enclosure_inner_depth / 2 - enclosure.front_thickness / 2
    window_probe = (
        cq.Workplane("XY", origin=(0, front_y, 0))
        .box(
            DESIGN.enclosure_window_width - 0.5,
            enclosure.front_thickness + 1,
            DESIGN.enclosure_window_height - 0.5,
        )
        .edges("|Y")
        .fillet(enclosure.window_corner_radius)
        .val()
    )
    assert shell.intersect(window_probe).Volume() == pytest.approx(0)

    drum_offset = -DESIGN.drum_outer_width / 2
    oriented_drum = cq.Compound.makeCompound(
        [
            _orient_for_enclosure(shape, drum_offset)
            for shape in drum_component_shapes().values()
        ]
    )
    assert shell.intersect(oriented_drum).Volume() == pytest.approx(0)


def test_enclosure_assemblies_contain_two_shell_parts() -> None:
    enclosure = enclosure_assembly()
    assert set(enclosure.objects) == {
        "alphabets-v2-drum-enclosure",
        "enclosure_upper",
        "enclosure_lower",
    }
    assert enclosure.toCompound().isValid()

    module = enclosed_module_assembly()
    assert {"enclosure_upper", "enclosure_lower"} < set(module.objects)
    assert module.toCompound().isValid()

    components = enclosed_module_components(exploded=True)
    assert len(components) == 202
    assert all(component.shape.isValid() for component in components)
    assert {"card_00", "card_63"} < {component.name for component in components}


def test_cq_editor_enclosure_entry_point_builds_exploded_module() -> None:
    namespace = runpy.run_path(str(MECHANICAL_DIR / "view_enclosure.py"))
    result = namespace["result"]
    assert isinstance(result, cq.Assembly)
    assert result.name == "alphabets-v2-enclosed-module"
    assert result.toCompound().isValid()
    assert len(namespace["objects"]) == 202
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
    assert manifest["units"] == "mm"
    assert manifest["parameters"]["drum"]["positions"] == 64
    assert manifest["geometry"]["drum_assembly"]["valid"] is True
    assert manifest["geometry"]["enclosure_upper"]["solid_count"] == 1
    assert manifest["geometry"]["enclosure_lower"]["solid_count"] == 1

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
