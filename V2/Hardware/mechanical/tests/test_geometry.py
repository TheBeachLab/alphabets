from __future__ import annotations

import json
import re
from fractions import Fraction
from pathlib import Path

import cadquery as cq
import ezdxf
import pytest

from alphabets_cad.assemblies import drum_component_shapes, module_reference_assembly
from alphabets_cad.parameters import DESIGN
from alphabets_cad.parts import (
    card_points,
    drum_support,
    enclosure_reference_edges,
    flap_card,
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


def test_flap_card_matches_current_cutter_geometry() -> None:
    card = flap_card()
    assert card.isValid()
    assert_bounds(
        card,
        (DESIGN.card.overall_width, DESIGN.card.total_height, DESIGN.card.thickness),
    )
    assert card.Volume() == pytest.approx(
        (
            DESIGN.card.body_width * DESIGN.card.body_height
            + DESIGN.card.overall_width * DESIGN.card.tab_height
        )
        * DESIGN.card.thickness
    )
    assert card_points()[0] == (0.0, 0.0)
    assert card_points()[5] == (-DESIGN.card.tab_width, DESIGN.card.total_height)


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
