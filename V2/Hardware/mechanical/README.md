# Alphabets V2 Definitivo mechanical CAD

This CadQuery model is the manufacturing source for **V2 Definitivo** only:
the 50 mm card, 51 mm internal drum width and its two-piece, open-rear
enclosure. The 55 mm **V2 Prototipo** has a different drum width and only a
historical enclosure reference; it must not be generated from this model.
The complete split is recorded in [`../../variants/`](../../variants/README.md).

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
| Two-part drum enclosure | Native CadQuery design around the current V2 drum | Printable prototype; validate fits physically |

`../structure/connector.scad` is an empty placeholder, so it contains no
mechanical geometry to reconstruct.

The FreeCAD `side_motor.FCStd` document contains four mesh features from an
older, wider drum and an enclosure sketch, rather than a parametric finished
part. Its meshes remain in `../structure/` as historical reference. The
CadQuery drum uses the current 50 mm flap width, 51 mm internal spacing and
55.3 mm assembled outer width.

## Two-part drum enclosure

The printable enclosure is a compact upper/lower clamshell inspired by the
clean, individual-cell language of Vestaboard modules. Its horizontal joint
follows the drum axis and the visual split between flap halves. The rear is
fully open for loading the drum, routing wires and servicing the mechanism.

The enclosure body is 64.1 mm wide, 92 mm deep and 93.8 mm high. Two small
rear screw lugs bring the local maximum width to 75.5 mm. The drum has 2 mm
nominal radial and axial clearance, and the front opening is 52 × 50 mm with
rounded corners. The motor-side wall includes the nominal 28BYJ-48 centre and
mounting holes; the shaft side has a 3.4 mm axle bore.

Assembly uses two M3 × 12 mm screws from the upper rear lugs into 2.6 mm pilot
holes in the lower lugs. Print both halves with the horizontal split plane on
the bed. The upper and lower STL files use assembly coordinates, so rotate the
lower half 180 degrees before slicing. Verify pilot fit, axle fit, the exact
motor variant and flap clearance on one module before printing an array.

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

`generate.py --variant prototype` deliberately stops before writing files,
because the old enclosure is not a validated parametric manufacturing source.

## Graphical editing

Open the complete reference module in CQ-editor from this directory:

```sh
make gui
```

Open an exploded view of the enclosure, drum and motor with:

```sh
make gui-enclosure
```

The enclosure view mounts all 64 cards as a clearance reference. The drum is
held at the card stop: half a 64-position pitch (2.8125°). The motor shaft is
rotated 90° to match the slotted motor-side disc hole, while the tab hinge axes
are centred on each flap hole. `card_31` (upper) and `card_32` (lower) are the two vertical
front cards. The lower/front and all southern cards hang with gravity; the
northern cards form the rear-to-front support stack, with the upper/front card
shown vertical on the pawl.

`design.toml` is the committed source for every direct manufacturing dimension.
Derived values — for example the drum's inner width and the enclosure's overall
width — remain calculated by the model and cannot drift. `view.py` exposes the
resolved `parameters`, each named shape in `objects`, and the export assembly in
`result`. CQ-editor therefore shows the parts separately instead of one opaque
assembly.

For a fit or fabrication variant, create a small TOML file containing only the
dimensions that change, then use the same profile for preview and export:

```sh
make gui PROFILE=profiles/fit-check.toml
make generate PROFILE=profiles/fit-check.toml OUTPUT=generated/fit-check
```

The profile is applied over the committed design, and unknown section or field
names fail immediately instead of silently changing the model.

### VS Code viewer

OCP CAD Viewer is the preferred interactive viewer: it inherits VS Code's
theme, provides per-object selection and visibility, and renders this model
through `view_vscode.py`. Run `view_enclosure_vscode.py` for the exploded
enclosure, drum, flap and motor as 11 independent objects. Install its isolated
environment once, then open this mechanical directory in VS Code and run the
file:

```sh
make setup-vscode
code alphabets-mechanical.code-workspace
```

Open the supplied workspace file rather than the repository root: it selects
the dedicated interpreter and the viewer's `browser` theme. It uses the same
optional `ALPHABETS_PROFILE` value as CQ-editor, so a selected profile changes
both views and generated fabrication files consistently.

The generated files are committed so a fabricator does not need CadQuery:

- `generated/cut/*.dxf`: millimetre cutter profiles;
- `generated/print/*.stl`: spool sides and both printable enclosure halves;
- `generated/step/*.step`: individual parts and complete reference assemblies;
- `generated/preview/*.svg`: assembled and exploded review projections;
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
