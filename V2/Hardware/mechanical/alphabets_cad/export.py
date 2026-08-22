# SPDX-License-Identifier: MIT
"""Deterministic manufacturing exports for the CadQuery model."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

import cadquery as cq
from cadquery.occ_impl.exporters.dxf import DxfDocument

from .assemblies import (
    drum_assembly,
    enclosed_module_assembly,
    enclosure_assembly,
    module_reference_assembly,
)
from .parameters import DESIGN, DesignParameters
from .parts import (
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


def generate(output_root: Path, params: DesignParameters = DESIGN) -> None:
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

    manifest = {
        "schema_version": 1,
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
                "native CadQuery design sized from "
                "V2/Hardware/blender/generated/card-envelope.json"
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
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
