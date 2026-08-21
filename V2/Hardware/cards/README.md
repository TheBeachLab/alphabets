# V2 Definitivo card and drum width

This directory is the **V2 Definitivo** 50 mm card route. The incompatible
55 mm **V2 Prototipo** card remains preserved as `card.fcstd`; its complete
physical contract is in [`../../variants/`](../../variants/README.md).

The production card uses one half of the `45 × 91 mm` sticker sheet:

- visible body: the complete central `50 × 48 mm` surface;
- total card: `50 × 48 mm`;
- side tabs: `4 × 2.5 mm` each; their bare `0.5 mm` thickness is included in the
  pivot fit, leaving at least `0.15 mm` radial clearance in the `3 mm` holes;
- total width across the tabs: `58 mm`;
- black card substrate: `0.5 mm`;
- sticker face: `45 × 45.5 mm`, centred with `2.5 mm` lateral margin and ending
  where the lateral tabs begin;
- one `0.1 mm` sticker on each face, for `0.7 mm` finished body thickness;
- the visible colour comes from the sticker, not from the substrate model.

The two drum sides are separated by `51 mm`: the `50 mm` card body plus
`1 mm` total axial clearance. The drum keeps its `85 mm` diameter and all 64
flap positions.

## Current manufacturing source

The card is now generated with the complete V2 mechanical model in
[`../mechanical/`](../mechanical/README.md). That model produces the current
DXF and STEP together with the matching drum and validates their shared
dimensions automatically.

## Preserved FreeCAD files

- `card-50x48.fcstd`: editable FreeCAD model and dimensional parameter sheet;
- `card-50x48-cut.svg`: exact vector cutter outline in millimetres;
- `card-50x48-cut.dxf`: the same closed outline on the `CUT` layer;
- `card-50x48.json`: manufacturing dimensions and the card/sticker/drum match.

The earlier FreeCAD representation can still be regenerated from the repository
root with:

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd \
  V2/Hardware/cards/generate_card.py
```

The regenerated `card.fcstd`, `card-cut.svg`, `card-cut.dxf`, and `card.json`
describe the 55 × 43 mm prototype geometry with its corrected 0.5 mm substrate.
Generate either geometry explicitly with FreeCADCmd:

```sh
# Definitivo: 50 × 48 mm card.
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd \
  V2/Hardware/cards/generate_card.py --pass '--variant definitive'

# Prototipo: 55 × 43 mm card; choose a separate output directory.
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd \
  V2/Hardware/cards/generate_card.py \
  --pass '--variant prototype --output-dir /tmp/alphabets-v2-prototype-card'
```

## Drum

`../structure/spool.scad` derives the drum separation from `flap_width = 50`
and `axial_clearance = 1`. Its `part` selector renders the side disc, the
shortened spacer, a cutting layout containing both, or the assembled drum:

```sh
openscad -o V2/Hardware/structure/spool-50mm.dxf \
  -D 'make3d=false' -D 'part="layout"' \
  V2/Hardware/structure/spool.scad
```

The assembled outer drum width is `55.3 mm`: `51 mm` between the inner faces
plus two `2.15 mm` side discs. Render it with `-D 'part="assembly"'`.
The generated `../structure/spool-50mm.dxf` contains the 85 mm side disc and
the shortened spacer cutting geometry; cut two copies of the side disc for one
drum.

The old 55 mm card spacing can still be reproduced explicitly with
`-D 'flap_width=55'`.
