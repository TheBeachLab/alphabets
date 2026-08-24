<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# Alphabets V2 Prototype mechanical CAD

[← Prototype stickers](../stickers/README.md) · [Physical variants](../../variants/README.md) · [Final CAD →](../../Final/mechanical/README.md)

This directory is an isolated CadQuery source for **V2 Prototype**. It is a
copy of the last trusted V2 Final source—the source used for the printed model
confirmed on 2026-08-23—with the complete Prototype profile applied. Prototype
and Final parts must not be mixed.

![Prototype enclosure and mechanism](generated/captured-enclosure/preview/captured-enclosure-module.svg)

## Matched Prototype profile

| Part | Prototype value |
| --- | ---: |
| Character order | `demo-64` |
| Card body | 55 × 43 × 0.5 mm |
| Card including tabs | 63 × 43 mm |
| Tab | 4 × 3 mm on each side |
| Sticker sheet item | 50 × 80 mm, cut at 40 mm |
| Sticker on each card face | 50 × 40 × 0.1 mm |
| Drum | 64 positions, 85 mm diameter |
| Drum inner / outer width | 56 / 60.3 mm |
| Visible pawl | Prototype, 3 mm longer than Final |

The sticker starts 3 mm from the card's free edge and reaches the hinge edge.
The complete 43 mm card remains visible; the 3 mm free-edge strip is simply
unstickered.

## Enclosure provenance and limit

`reference/cards-position-capture-final.json` is a local, unchanged copy of
the settled transforms from the trusted Final capture at frame 27464. CadQuery
rebuilds the cards, stickers, drum width and pawl from this directory's
`design.toml`, then applies those transforms. This gives a reproducible
Prototype derivative without reviving the stale FreeCAD enclosure or old
rendered files.

This is a valid parametric and exportable model, but it is **not yet a
physically validated Prototype enclosure**. Its height and depth remain
conservative values derived from the trusted Final motion capture. Print one
complete Prototype module and check the real card motion, pawl, motor, shaft,
stacking keys and cable clearance before reproducing it.

The historical Prototype contract also has one explicit fit exception: the
corner radius of a rectangular 3 × 0.5 mm tab is about 1.5207 mm, approximately
0.0207 mm larger than the radius of its nominal 3 mm pivot hole. The model
records this as `allow_tab_interference = true`; it does not claim theoretical
rotation clearance. Confirm the real material, kerf and hole fit with a small
sample.

## Rebuild and test

CadQuery 2.8.0 runs under Python 3.12:

```sh
cd V2/Hardware/Prototype/mechanical
make setup
make check
```

To reuse another compatible environment:

```sh
make check PYTHON=/path/to/python
```

`make generate` creates the Prototype card, drum, motor references and neutral
manufacturing files. `make generate-captured-enclosure` creates the one-piece
enclosure, Prototype pawl, assembly, review image and a two-object Bambu Lab A1
Mini plate. The enclosure prints standing on its front rim, with the pawl
inside the open area of the same plate. `make verify-generated` regenerates
everything and fails if the committed outputs are stale.

## View and adjust

All direct dimensions are in [`design.toml`](design.toml). Derived dimensions
are calculated in `alphabets_cad/parameters.py`, so card, drum and enclosure
widths cannot silently drift apart.

The primary `[drum_enclosure]` controls use the drum centre as their origin:

| Parameter | Meaning |
| --- | --- |
| `top_distance` | Drum centre to the inside of the top wall |
| `bottom_distance` | Drum centre to the inside floor |
| `back_distance` | Drum centre to the inside back edge |
| `side_clearance` | Gap from each outside drum face to its inside enclosure wall |
| `wall_thickness` | Enclosure thickness on the sides, top and bottom |
| `side_inset_depth` | Shared motor/electronics and opposite-side recess depth |

The front follows the saved front-card/pawl plane. `front_chamfer` is derived
as `wall_thickness / 2`, and the material left behind both side recesses is
`wall_thickness - side_inset_depth`.

The enclosure is one continuous shell. It has no horizontal assembly seam,
magnet pockets or internal alignment keys. Four external truncated pyramids on
the bottom and their four top sockets align complete modules when stacked.

Captured card angles come from the settled Blender snapshot, while every card
tab axis is rebuilt on the exact calculated centre of its rotated drum hole.
The Prototype viewer does not inherit Blender hinge-constraint drift or the
different centroid of the Final card used by that snapshot.

For VS Code with OCP CAD Viewer:

```sh
make setup-vscode
code alphabets-prototype-mechanical.code-workspace
```

Run `view_enclosure_vscode.py`. The groups include `enclosure`,
`pua_prototipo`, `tambor`, `cards`, `stickers`, `motor`, `electronics` and
`envelopes`; the Final pawl starts hidden. CQ-editor users can run `make gui`
or `make gui-enclosure`.

## Generated fabrication files

- `generated/cut/flap-card.dxf`: Prototype card cutter profile.
- `generated/step/flap-card.step`: neutral 3D card model.
- `generated/cut/drum-*.dxf`: matched 56 mm internal-width drum parts.
- `generated/captured-enclosure/print/`: one-piece enclosure STL, Prototype
  pawl and two-object A1 Mini plate.
- `generated/captured-enclosure/step/`: enclosure, pawl and assembly STEP.
- `generated/manifest.json` and `generated/captured-enclosure/manifest.json`:
  exact dimensions, bounds, source lineage and validation boundary.

The matching Demo‑64 artwork and cutter files are in
[`../stickers/generated`](../stickers/README.md).

[← Prototype stickers](../stickers/README.md) · [Physical variants](../../variants/README.md) · [Final CAD →](../../Final/mechanical/README.md)
