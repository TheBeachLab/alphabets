# Alphabets V2 mechanical CAD

CadQuery is the editable source of truth for the current V2 mechanical
geometry. It centralizes the dimensions that were previously split across
OpenSCAD, FreeCAD and generated cutter files, and produces vendor-neutral
manufacturing exports without GUI interaction.

## Included geometry

| CadQuery model | Source reconstructed | Status |
| --- | --- | --- |
| 50 × 48 mm flap card | `../cards/generate_card.py` | Current dimensional design |
| 64-position laser-cut drum | `../structure/spool.scad` | Current dimensional design |
| Lightweight printed spool | `../structure/spool-3dp.scad` | Legacy manufacturing alternative; validate physically |
| 28BYJ-48 motor | `../structure/28byj48.scad` | Clearance reference only |
| Holder side and inset | dormant `side()` and active `inset()` in `../structure/spool-holder.scad` | Legacy reference; validate physically |
| Enclosure sketch | `Sketch` in `../structure/side_motor.FCStd` | Exact non-solid reference geometry |

`../structure/connector.scad` is an empty placeholder, so it contains no
mechanical geometry to reconstruct.

The FreeCAD `side_motor.FCStd` document contains four mesh features from an
older, wider drum and an enclosure sketch, rather than a parametric finished
part. Its meshes remain in `../structure/` as historical reference. The
CadQuery drum uses the current 50 mm flap width, 51 mm internal spacing and
55.3 mm assembled outer width.

## Rebuild

CadQuery 2.8.0 is pinned and runs under Python 3.12:

```sh
cd V2/Hardware/mechanical
make setup
make check
```

To use an existing environment:

```sh
make check PYTHON=/path/to/python
```

The generated files are committed so a fabricator does not need CadQuery:

- `generated/cut/*.dxf`: millimetre cutter profiles;
- `generated/print/*.stl`: 3D-printable legacy spool sides;
- `generated/step/*.step`: card, drum, motor reference and reference module;
- `generated/preview/module-reference.svg`: review projection;
- `generated/manifest.json`: dimensions, provenance, bounding boxes and
  validation status.

`make verify-generated` regenerates everything, executes the geometry tests
and fails if the committed outputs are stale.

## Fabrication boundary

The card and laser-cut drum reproduce the current repository dimensions. The
motor model is a nominal clearance envelope. Motor variation, material
thickness, kerf, shaft fit, sensor placement and the holder/enclosure references
still require measurement on the physical module before a production order.
STEP is the exchange format for downstream CAD; DXF is the cutting source and
STL is used only for additive parts.
