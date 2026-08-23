# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Deterministic manufacturing exports for the CadQuery model."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

import cadquery as cq
from cadquery.occ_impl.exporters.dxf import DxfDocument

CODE_DIR = Path(__file__).resolve().parents[3] / "Code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from artifact_license_metadata import embed_artifact_license
from json_license_metadata import write_licensed_json

from .assemblies import (
    captured_enclosure_design_components,
    drum_assembly,
    enclosed_module_assembly,
    enclosure_assembly,
    module_reference_assembly,
)
from .parameters import DESIGN, DesignParameters
from .parts import (
    captured_drum_enclosure_parts,
    captured_enclosure_limits,
    captured_pawl_parts,
    drum_enclosure_parts,
    drum_support,
    enclosure_reference_edges,
    flap_card,
    laser_cut_disc,
    legacy_holder_inset,
    legacy_holder_side,
    motor_reference,
    printed_spool_disc,
)

NORMALIZED_TIMESTAMP = "1970-01-01T00:00:00"
NORMALIZED_DXF_DATE = "2440587.5"
A1_MINI_BUILD_VOLUME_MM = (180.0, 180.0, 180.0)
A1_MINI_PLATE_MARGIN_MM = 5.0
A1_MINI_PART_GAP_MM = 2.0


def _place_on_plate(
    shape: cq.Shape,
    *,
    x: float,
    y: float,
    x_rotation: float,
    z_rotation: float = 0,
) -> cq.Shape:
    oriented = shape.rotate((0, 0, 0), (1, 0, 0), x_rotation)
    if z_rotation:
        oriented = oriented.rotate((0, 0, 0), (0, 0, 1), z_rotation)
    box = oriented.BoundingBox()
    return oriented.translate((x - box.xmin, y - box.ymin, -box.zmin))


def _captured_bambu_a1_mini_plate(
    parts: dict[str, cq.Shape],
    pawls: dict[str, cq.Shape],
    pawl_variants: tuple[str, ...] = ("definitive", "prototype"),
) -> tuple[cq.Shape, dict[str, dict[str, object]]]:
    """Lay out one isolated variant's parts inside the A1 mini build volume."""

    margin = A1_MINI_PLATE_MARGIN_MM
    gap = A1_MINI_PART_GAP_MM
    upper_preview = _place_on_plate(parts["enclosure_upper"], x=0, y=0, x_rotation=-90)
    lower_preview = _place_on_plate(parts["enclosure_lower"], x=0, y=0, x_rotation=-90)
    upper_size = upper_preview.BoundingBox()
    lower_size = lower_preview.BoundingBox()
    # With the front rims on the bed, the two halves fit the A1 Mini only when
    # arranged side by side. This also keeps them in their assembled relation,
    # separated by the requested small printable gap.
    group_width = lower_size.xlen + gap + upper_size.xlen
    group_height = max(lower_size.ylen, upper_size.ylen)
    group_x = (A1_MINI_BUILD_VOLUME_MM[0] - group_width) / 2
    group_y = (A1_MINI_BUILD_VOLUME_MM[1] - group_height) / 2
    lower_x = group_x
    upper_x = lower_x + lower_size.xlen + gap
    lower_y = group_y + (group_height - lower_size.ylen) / 2
    upper_y = group_y + (group_height - upper_size.ylen) / 2
    pawl_names = tuple(f"pawl_{variant}" for variant in pawl_variants)
    pawl_sizes = {
        name: _place_on_plate(pawls[name], x=0, y=0, x_rotation=90).BoundingBox()
        for name in pawl_names
    }
    pawl_gap = 10.0
    pawl_group_width = sum(size.xlen for size in pawl_sizes.values()) + pawl_gap * max(
        0, len(pawl_sizes) - 1
    )
    pawl_x = lower_x + (lower_size.xlen - pawl_group_width) / 2
    pawl_y = (
        lower_y + (lower_size.ylen - max(size.ylen for size in pawl_sizes.values())) / 2
    ) + gap
    placements = {
        "enclosure_upper": _place_on_plate(
            parts["enclosure_upper"],
            x=upper_x,
            y=upper_y,
            x_rotation=-90,
        ),
        "enclosure_lower": _place_on_plate(
            parts["enclosure_lower"],
            x=lower_x,
            y=lower_y,
            x_rotation=-90,
        ),
    }
    current_pawl_x = pawl_x
    for name in pawl_names:
        placements[name] = _place_on_plate(
            pawls[name], x=current_pawl_x, y=pawl_y, x_rotation=90
        )
        current_pawl_x += pawl_sizes[name].xlen + pawl_gap
    plate = cq.Compound.makeCompound(list(placements.values()))
    plate_box = plate.BoundingBox()
    build_x, build_y, build_z = A1_MINI_BUILD_VOLUME_MM
    if (
        plate_box.xmin < margin
        or plate_box.ymin < margin
        or plate_box.xmax > build_x - margin
        or plate_box.ymax > build_y - margin
    ):
        raise ValueError("captured enclosure parts do not fit the A1 mini plate")
    if plate_box.zmax > build_z:
        raise ValueError("captured enclosure parts exceed the A1 mini build height")
    placement_values = list(placements.values())
    for index, first in enumerate(placement_values):
        for second in placement_values[index + 1 :]:
            if first.intersect(second).Volume() > 1e-6:
                raise ValueError(
                    "captured enclosure parts overlap on the A1 mini plate"
                )

    layout = {}
    for name, shape in placements.items():
        box = shape.BoundingBox()
        layout[name] = {
            "bounds_mm": {
                "x": [round(box.xmin, 6), round(box.xmax, 6)],
                "y": [round(box.ymin, 6), round(box.ymax, 6)],
                "z": [round(box.zmin, 6), round(box.zmax, 6)],
            },
            "bed_face": (
                "front enclosure rim"
                if name.startswith("enclosure")
                else "flat rear face"
            ),
            "rotation_deg": (
                {"x": -90, "z": 0}
                if name.startswith("enclosure")
                else {"x": 90, "z": 0}
            ),
        }
    return plate, layout


def generate_captured_enclosure(
    output_root: Path,
    capture_path: Path,
    params: DesignParameters = DESIGN,
    physical_variant: str | None = None,
) -> None:
    """Export the two-part enclosure fitted to a settled Blender capture."""

    if physical_variant not in {None, "prototype", "definitive"}:
        raise ValueError(f"unknown physical variant: {physical_variant!r}")

    output_root = output_root.resolve()
    directories = {name: output_root / name for name in ("print", "step", "preview")}
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    capture_variant = capture.get("physical_variant")
    if physical_variant is not None and capture_variant != physical_variant:
        raise ValueError(
            f"capture is for {capture_variant!r}, not {physical_variant!r}"
        )
    parts = captured_drum_enclosure_parts(capture, params)
    pawls = captured_pawl_parts(capture, params)
    pawl_variants = (
        (physical_variant,) if physical_variant else ("definitive", "prototype")
    )
    active_pawl_name = f"pawl_{physical_variant or 'definitive'}"
    assembly = cq.Compound.makeCompound([*parts.values(), pawls[active_pawl_name]])
    limits = captured_enclosure_limits(capture, params)
    remaining_docking_gap = (
        params.motor.chassis_height
        - params.drum_enclosure.motor_inset_depth
        - params.drum_enclosure.docking_recess_depth
        + params.drum_enclosure.docking_clearance
    )

    for half in ("upper", "lower"):
        shape = parts[f"enclosure_{half}"]
        _export_step(
            shape,
            directories["step"] / f"captured-enclosure-{half}.step",
        )
        stl_path = directories["print"] / f"captured-enclosure-{half}.stl"
        shape.exportStl(
            str(stl_path),
            tolerance=0.08,
            angularTolerance=0.125,
        )
        embed_artifact_license(stl_path)
    for variant in pawl_variants:
        shape = pawls[f"pawl_{variant}"]
        pawl_stem = (
            "captured-enclosure-pawl"
            if physical_variant
            else f"captured-enclosure-pawl-{variant}"
        )
        _export_step(
            shape,
            directories["step"] / f"{pawl_stem}.step",
        )
        stl_path = directories["print"] / f"{pawl_stem}.stl"
        shape.exportStl(
            str(stl_path),
            tolerance=0.05,
            angularTolerance=0.1,
        )
        embed_artifact_license(stl_path)
    print_plate, print_plate_layout = _captured_bambu_a1_mini_plate(
        parts, pawls, pawl_variants
    )
    print_plate_summary = _shape_summary(print_plate)
    plate_filename = (
        "captured-enclosure-print-plate.stl"
        if physical_variant
        else "captured-enclosure-bambu-a1-mini-four-part-plate.stl"
    )
    print_plate_path = directories["print"] / plate_filename
    print_plate.exportStl(
        str(print_plate_path),
        tolerance=0.08,
        angularTolerance=0.125,
    )
    embed_artifact_license(print_plate_path)
    _export_step(
        assembly,
        directories["step"] / "captured-enclosure-assembly.step",
    )

    review_components = captured_enclosure_design_components(capture_path, params)
    review = cq.Compound.makeCompound(
        [
            component.shape
            for component in review_components
            if component.name != "pawl_prototype"
        ]
    )
    preview_path = directories["preview"] / "captured-enclosure-module.svg"
    cq.exporters.export(
        review,
        str(preview_path),
        exportType="SVG",
        opt={
            "width": 900,
            "height": 900,
            "marginLeft": 30,
            "marginTop": 30,
            "projectionDir": (1.0, -1.3, 0.8),
            "showAxes": False,
            "showHidden": True,
            "strokeWidth": 0.35,
        },
    )
    _strip_trailing_whitespace(preview_path)
    embed_artifact_license(preview_path)

    manifest = {
        "schema_version": 1,
        "physical_variant": physical_variant,
        "units": "mm",
        "cad_engine": "CadQuery 2.8.0 / OCCT",
        "capture": {
            "file": capture_path.name,
            "frame": capture["capture_frame"],
            "controller": capture["controller"],
        },
        "limits_mm": asdict(limits),
        "parameters": {
            "wall_thickness": params.drum_enclosure.capture_wall_thickness,
            "floor_thickness": params.drum_enclosure.floor_thickness,
            "axial_clearance": params.drum_enclosure.axial_clearance,
            "capture_card_clearance": (params.drum_enclosure.capture_card_clearance),
            "capture_top_clearance": params.drum_enclosure.capture_top_clearance,
            "outer_corner_radius": (params.drum_enclosure.capture_outer_corner_radius),
            "capture_split_height": params.drum_enclosure.capture_split_height,
            "front_inner_chamfer": params.drum_enclosure.front_inner_chamfer,
            "motor_inset_depth": params.drum_enclosure.motor_inset_depth,
            "docking_recess_depth": params.drum_enclosure.docking_recess_depth,
            "docking_clearance": params.drum_enclosure.docking_clearance,
            "motor_cable_clearance": params.drum_enclosure.motor_cable_clearance,
            "side_feature_chamfer": params.drum_enclosure.side_feature_chamfer,
            "boss_end_chamfer": params.drum_enclosure.boss_end_chamfer,
            "electronics_card_width": params.drum_enclosure.electronics_card_width,
            "electronics_card_height": (params.drum_enclosure.electronics_card_height),
            "electronics_card_center_y": (
                params.drum_enclosure.electronics_card_center_y
            ),
            "electronics_card_center_z": (
                params.drum_enclosure.electronics_card_center_z
            ),
            "electronics_card_clearance": (
                params.drum_enclosure.electronics_card_clearance
            ),
            "motor_electronics_corner_radius": (
                params.drum_enclosure.motor_electronics_corner_radius
            ),
            "remaining_side_wall": (
                params.drum_enclosure.capture_wall_thickness
                - params.drum_enclosure.motor_inset_depth
            ),
            "minimum_same_orientation_gap": remaining_docking_gap,
            "minimum_same_orientation_pitch": (
                limits.outer_width + remaining_docking_gap
            ),
            "motor_bore_diameter": params.drum_enclosure.motor_bore_diameter,
            "motor_mount_pilot_diameter": (params.drum_enclosure.screw_pilot_diameter),
            "motor_mount_boss_radius": (params.drum_enclosure.motor_mount_boss_radius),
            "motor_mount_disc_clearance": (
                params.drum_enclosure.motor_mount_disc_clearance
            ),
            "shaft_screw_clearance_diameter": 2 * params.drum.shaft_axis_radius,
            "shaft_support_pilot_diameter": (
                params.drum_enclosure.screw_pilot_diameter
            ),
            "shaft_support_boss_radius": (
                params.drum_enclosure.shaft_support_boss_radius
            ),
            "shaft_head_recess_diameter": (
                params.drum_enclosure.shaft_head_recess_diameter
            ),
            "shaft_head_recess_depth": (params.drum_enclosure.shaft_head_recess_depth),
            "shaft_support_axial_clearance": (
                params.drum_enclosure.shaft_support_axial_clearance
            ),
            "pawl_mount_width": params.drum_enclosure.pawl_mount_width,
            "pawl_pilot_diameter": params.drum_enclosure.screw_pilot_diameter,
            "pawl_pilot_depth": params.drum_enclosure.pawl_pilot_depth,
            "pawl_thickness_addition": (params.drum_enclosure.pawl_thickness_addition),
            "pawl_outer_chamfer": params.drum_enclosure.pawl_outer_chamfer,
            "pawl_head_recess_diameter": (
                params.drum_enclosure.pawl_head_recess_diameter
            ),
            "pawl_head_recess_depth": (params.drum_enclosure.pawl_head_recess_depth),
            "pawl_tip_radius": params.drum_enclosure.pawl_tip_radius,
            "pawl_screw_clearance_diameter": (
                params.drum_enclosure.screw_clearance_diameter
            ),
            "prototype_pawl_extension": (
                params.drum_enclosure.prototype_pawl_extension
            ),
            "alignment_height": params.drum_enclosure.alignment_height,
            "alignment_base_size": params.drum_enclosure.alignment_base_size,
            "alignment_top_size": params.drum_enclosure.alignment_top_size,
            "alignment_clearance": params.drum_enclosure.alignment_clearance,
            "stack_alignment_x_inset": (params.drum_enclosure.stack_alignment_x_inset),
            "stack_alignment_y_inset": (params.drum_enclosure.stack_alignment_y_inset),
            "top_mark_character": params.drum_enclosure.top_mark_character,
            "top_mark_font": "Overpass Mono Medium",
            "top_mark_font_size": params.drum_enclosure.top_mark_font_size,
            "top_mark_depth": params.drum_enclosure.top_mark_depth,
            "top_mark_chamfer": params.drum_enclosure.top_mark_chamfer,
            "top_mark_split_gap": params.drum_enclosure.top_mark_split_gap,
            "top_mark_rotation": params.drum_enclosure.top_mark_rotation,
            "magnet_diameter": params.drum_enclosure.magnet_diameter,
            "magnet_thickness": params.drum_enclosure.magnet_thickness,
            "magnet_radial_clearance": (params.drum_enclosure.magnet_radial_clearance),
            "magnet_depth_clearance": (params.drum_enclosure.magnet_depth_clearance),
            "split_gap": params.drum_enclosure.split_gap,
        },
        "features": {
            "front_open": True,
            "rear_open": True,
            "screw_lugs": False,
            "replaceable_pawls": (
                "one variant-specific pawl with a 1 mm outer-face chamfer, "
                "retained by one M3 screw into a self-tapping pilot"
                if physical_variant
                else "legacy combined export containing both pawl lengths"
            ),
            "visible_assembly_pawl": physical_variant or "definitive",
            "lower_shaft_support": (
                "M3 self-tapping pilot in a 9 mm boss tapered continuously "
                "from the inside wall; user-supplied M3 screw forms the axle "
                "through the drum's 3.4 mm clearance hole"
            ),
            "motor_mount": (
                "two M3 self-tapping pilots in internal bosses tapered "
                "continuously from the inside wall"
            ),
            "motor_electronics_pocket": (
                "single approximately 55.7 x 76.6 mm rounded-rectangle side "
                "pocket around the "
                "motor and a 50 x 35 mm electronics-card envelope, with an "
                "8 mm inner corner radius and continuous 6 mm lead-in"
            ),
            "split_magnets": (
                "one unchamfered 3.4 x 1.2 mm magnet insert per side and per "
                "half for nominal 3 x 1 mm magnets"
            ),
            "vertical_stack_magnets": (
                "one centred unchamfered 3.4 x 1.2 mm insert in the alpha "
                "top face and one matching insert in the module base"
            ),
            "part_alignment": (
                "four 3 mm truncated pyramids with 45 degree sides and "
                "0.2 mm socket clearance"
            ),
            "vertical_stacking": (
                "four downward 3 mm truncated pyramids and four matching "
                "top sockets with 0.2 mm clearance, inset to the tangent of "
                "the 10 mm enclosure corner radius"
            ),
            "front_edge": ("4 mm inner chamfer with a flat mounting land at the pawl"),
            "front_bed_printing": (
                "6 mm 45 degree lead-ins on both side recesses and a 2 mm "
                "lead-in through the remaining motor bore wall; screw pilots "
                "remain cylindrical"
            ),
            "top_mark": (
                "large split alpha rotated toward the front and recessed "
                "0.2 mm into the upper face through a nominal 0.2 mm chamfer"
            ),
            "side_docking_relief": (
                f"{params.drum_enclosure.motor_inset_depth:g} mm motor inset plus "
                f"{params.drum_enclosure.docking_recess_depth:g} mm opposite "
                f"recess; {remaining_docking_gap:g} mm body gap still required "
                "for equal orientation"
            ),
        },
        "geometry": {
            name: _shape_summary(shape)
            for name, shape in {
                **parts,
                **{
                    f"pawl_{variant}": pawls[f"pawl_{variant}"]
                    for variant in pawl_variants
                },
            }.items()
        },
        "print_plate": {
            "file": f"print/{plate_filename}",
            "printer": "Bambu Lab A1 mini",
            "build_volume_mm": list(A1_MINI_BUILD_VOLUME_MM),
            "margin_mm": A1_MINI_PLATE_MARGIN_MM,
            "part_gap_mm": A1_MINI_PART_GAP_MM,
            "geometry": print_plate_summary,
            "parts": print_plate_layout,
        },
        "fabrication_status": (
            "Parametric prototype derived from the captured settled mechanism; "
            "clearances and print orientation require physical fit validation before "
            "final fabrication."
        ),
    }
    write_licensed_json(output_root / "manifest.json", manifest, sort_keys=True)


def _strip_trailing_whitespace(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(
        "\n".join(line.rstrip() for line in text.splitlines()) + "\n",
        encoding="utf-8",
    )


def _normalize_dxf(path: Path) -> None:
    """Remove ezdxf timestamps and UUIDs so committed outputs are reproducible."""

    text = path.read_text(encoding="utf-8")
    for variable in ("TDCREATE", "TDUPDATE"):
        text = re.sub(
            rf"(\${variable}\n\s*40\n)[^\n]+",
            rf"\g<1>{NORMALIZED_DXF_DATE}",
            text,
        )
    text = re.sub(
        r"(\$FINGERPRINTGUID\n\s*2\n)[^\n]+",
        r"\g<1>{00000000-0000-0000-0000-000000000001}",
        text,
    )
    text = re.sub(
        r"(\$VERSIONGUID\n\s*2\n)[^\n]+",
        r"\g<1>{00000000-0000-0000-0000-000000000002}",
        text,
    )
    text = re.sub(
        r"(\d+\.\d+\.\d+ @ )[^\n]+",
        rf"\g<1>{NORMALIZED_TIMESTAMP}+00:00",
        text,
    )
    path.write_text(text, encoding="utf-8")


def _normalize_step(path: Path) -> None:
    """Remove the OCCT export timestamp from an otherwise stable STEP file."""

    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"(FILE_NAME\('[^']*',)'[^']*'",
        rf"\g<1>'{NORMALIZED_TIMESTAMP}'",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")
    _strip_trailing_whitespace(path)


def _export_step(model: cq.Shape | cq.Assembly, path: Path) -> None:
    model.export(str(path))
    _normalize_step(path)
    embed_artifact_license(path)


def _bottom_faces(shape: cq.Shape) -> cq.Compound:
    z_min = shape.BoundingBox().zmin
    faces = [
        face
        for face in shape.Faces()
        if abs(face.BoundingBox().zmin - z_min) < 1e-6 and face.normalAt().z < -0.99
    ]
    if not faces:
        raise ValueError("shape has no downward planar faces to export")
    return cq.Compound.makeCompound(faces)


def _export_dxf(
    path: Path,
    shapes: Iterable[tuple[str, cq.Shape]],
) -> None:
    document = DxfDocument(
        dxfversion="AC1015",
        doc_units=4,
        metadata={"title": "Alphabets V2 CadQuery manufacturing profile"},
    )
    added_layers: set[str] = set()
    for layer, shape in shapes:
        if layer not in added_layers:
            document.add_layer(layer, color=7)
            added_layers.add(layer)
        document.add_shape(_bottom_faces(shape), layer=layer)
    document.document.saveas(path)
    _normalize_dxf(path)
    embed_artifact_license(path)


def _export_reference_dxf(path: Path, shape: cq.Shape) -> None:
    document = DxfDocument(
        dxfversion="AC1015",
        doc_units=4,
        metadata={"title": "Alphabets V2 legacy enclosure sketch reference"},
    )
    document.add_layer("REFERENCE", color=8)
    document.add_shape(shape, layer="REFERENCE")
    document.document.saveas(path)
    _normalize_dxf(path)
    embed_artifact_license(path)


def _shape_summary(shape: cq.Shape) -> dict[str, object]:
    box = shape.BoundingBox()
    solids = shape.Solids()
    merged = solids[0]
    for solid in solids[1:]:
        merged = merged.fuse(solid)
    return {
        "valid": shape.isValid(),
        "solid_count": len(solids),
        "volume_mm3": round(merged.Volume(), 6),
        "component_volume_sum_mm3": round(shape.Volume(), 6),
        "bounds_mm": {
            "x": [round(box.xmin, 6), round(box.xmax, 6)],
            "y": [round(box.ymin, 6), round(box.ymax, 6)],
            "z": [round(box.zmin, 6), round(box.zmax, 6)],
        },
    }


def generate(
    output_root: Path,
    params: DesignParameters = DESIGN,
    physical_variant: str | None = None,
) -> None:
    output_root = output_root.resolve()
    directories = {
        name: output_root / name for name in ("cut", "print", "step", "preview")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    card = flap_card(params)
    motor_disc = laser_cut_disc(True, params)
    shaft_disc = laser_cut_disc(False, params)
    support = drum_support(params)
    holder = legacy_holder_side(params)
    holder_inset = legacy_holder_inset(params)
    printed_motor = printed_spool_disc(True, params)
    printed_shaft = printed_spool_disc(False, params)
    motor = motor_reference(params)
    drum = drum_assembly(params)
    module = module_reference_assembly(params)
    enclosure_parts = drum_enclosure_parts(params)
    enclosure = enclosure_assembly(params)
    enclosed_module = enclosed_module_assembly(params)
    exploded_enclosed_module = enclosed_module_assembly(params, exploded=True)
    geometry_summary = {
        "card": _shape_summary(card),
        "motor_disc": _shape_summary(motor_disc),
        "shaft_disc": _shape_summary(shaft_disc),
        "support": _shape_summary(support),
        "printed_motor_disc": _shape_summary(printed_motor),
        "printed_shaft_disc": _shape_summary(printed_shaft),
        "motor_reference": _shape_summary(motor),
        "drum_assembly": _shape_summary(drum.toCompound()),
        "module_reference": _shape_summary(module.toCompound()),
        "enclosure_upper": _shape_summary(enclosure_parts["enclosure_upper"]),
        "enclosure_lower": _shape_summary(enclosure_parts["enclosure_lower"]),
        "enclosure_assembly": _shape_summary(enclosure.toCompound()),
        "enclosed_module": _shape_summary(enclosed_module.toCompound()),
    }

    _export_dxf(directories["cut"] / "flap-card.dxf", [("CUT", card)])
    _export_dxf(
        directories["cut"] / "drum-motor-side.dxf",
        [("CUT", motor_disc)],
    )
    _export_dxf(
        directories["cut"] / "drum-shaft-side.dxf",
        [("CUT", shaft_disc)],
    )
    _export_dxf(
        directories["cut"] / "drum-support.dxf",
        [("CUT", support)],
    )
    _export_dxf(
        directories["cut"] / "legacy-holder-side.dxf",
        [("CUT", holder), ("INSET", holder_inset.translate((90, 0, 0)))],
    )
    _export_reference_dxf(
        directories["cut"] / "enclosure-sketch-reference.dxf",
        enclosure_reference_edges(params),
    )

    layout = [
        ("CUT", motor_disc),
        ("CUT", shaft_disc.translate((95, 0, 0))),
        ("CUT", support.translate((25, 78, 0))),
        ("CUT", support.translate((70, 78, 0))),
    ]
    _export_dxf(directories["cut"] / "drum-complete-layout.dxf", layout)

    _export_step(card, directories["step"] / "flap-card.step")
    _export_step(
        motor,
        directories["step"] / "motor-28byj48-reference.step",
    )
    _export_step(
        drum.toCompound(),
        directories["step"] / "drum-assembly.step",
    )
    _export_step(
        module.toCompound(),
        directories["step"] / "module-reference.step",
    )
    _export_step(
        enclosure_parts["enclosure_upper"],
        directories["step"] / "drum-enclosure-upper.step",
    )
    _export_step(
        enclosure_parts["enclosure_lower"],
        directories["step"] / "drum-enclosure-lower.step",
    )
    _export_step(
        enclosure.toCompound(),
        directories["step"] / "drum-enclosure-assembly.step",
    )
    _export_step(
        enclosed_module.toCompound(),
        directories["step"] / "enclosed-module-reference.step",
    )

    printed_motor.export(
        str(directories["print"] / "spool-motor-side.stl"),
        tolerance=0.08,
        angularTolerance=0.125,
    )
    printed_shaft.export(
        str(directories["print"] / "spool-shaft-side.stl"),
        tolerance=0.08,
        angularTolerance=0.125,
    )
    enclosure_parts["enclosure_upper"].exportStl(
        str(directories["print"] / "drum-enclosure-upper.stl"),
        tolerance=0.08,
        angularTolerance=0.125,
    )
    enclosure_parts["enclosure_lower"].exportStl(
        str(directories["print"] / "drum-enclosure-lower.stl"),
        tolerance=0.08,
        angularTolerance=0.125,
    )
    for path in directories["print"].glob("*.stl"):
        embed_artifact_license(path)

    cq.exporters.export(
        module.toCompound(),
        str(directories["preview"] / "module-reference.svg"),
        exportType="SVG",
        opt={
            "width": 900,
            "height": 700,
            "marginLeft": 30,
            "marginTop": 30,
            "projectionDir": (1.0, -1.0, 0.8),
            "showAxes": False,
            "showHidden": True,
            "strokeWidth": 0.35,
        },
    )
    _strip_trailing_whitespace(directories["preview"] / "module-reference.svg")
    embed_artifact_license(directories["preview"] / "module-reference.svg")

    for name, model in (
        ("enclosure-module", enclosed_module),
        ("enclosure-exploded", exploded_enclosed_module),
    ):
        cq.exporters.export(
            model.toCompound(),
            str(directories["preview"] / f"{name}.svg"),
            exportType="SVG",
            opt={
                "width": 900,
                "height": 700,
                "marginLeft": 30,
                "marginTop": 30,
                "projectionDir": (1.0, -1.3, 0.8),
                "showAxes": False,
                "showHidden": True,
                "strokeWidth": 0.35,
            },
        )
        _strip_trailing_whitespace(directories["preview"] / f"{name}.svg")
        embed_artifact_license(directories["preview"] / f"{name}.svg")

    manifest = {
        "schema_version": 1,
        "physical_variant": physical_variant,
        "units": "mm",
        "cad_engine": "CadQuery 2.8.0 / OCCT",
        "parameters": params.as_dict(),
        "source_lineage": {
            "card": "V2/Hardware/cards/generate_card.py",
            "laser_cut_drum": "V2/Hardware/structure/spool.scad",
            "printed_spool": "V2/Hardware/structure/spool-3dp.scad",
            "motor_reference": "V2/Hardware/structure/28byj48.scad",
            "holder_reference": "V2/Hardware/structure/spool-holder.scad side()",
            "enclosure_reference": "V2/Hardware/structure/side_motor.FCStd Sketch",
            "drum_enclosure": (
                "native CadQuery design sized from the selected "
                "V2/<variant>/generated/blender capture"
            ),
        },
        "geometry": geometry_summary,
        "fabrication_status": {
            "card_and_laser_cut_drum": "ported from current dimensional sources",
            "printed_spool": "ported legacy alternative; physical validation required",
            "motor": "clearance reference, not a manufacturing model",
            "holder_side": "ported dormant legacy profile; physical validation required",
            "enclosure_sketch": "non-solid reference geometry",
            "drum_enclosure": (
                "two symmetric printable halves sized from the captured card "
                "envelope; embedded magnetic coupling requires physical validation"
            ),
        },
    }
    write_licensed_json(output_root / "manifest.json", manifest, sort_keys=True)
