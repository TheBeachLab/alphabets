<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# V2 physical variants

`variants.json` is the authoritative contract that prevents parts from the two
incompatible V2 builds being mixed. A character order is inseparable from its
sticker sheet, card, drum spacing and enclosure source.

| Variant | Character preset | Sticker / halves | Card | Drum inner / outer width | Enclosure |
| --- | --- | --- | --- | --- | --- |
| **V2 Prototipo** | `demo-64` | 50 × 80 / 50 × 40 mm | 55 × 43 mm, all visible | 56 / 60.3 mm | historical FreeCAD reference only |
| **V2 Definitivo** | `international-64` | 45 × 91 / 45 × 45.5 mm | 50 × 48 mm, all visible | 51 / 55.3 mm | current two-piece, open-rear CadQuery source |

Both variants leave a 2.5 mm placement margin at each lateral edge. The sticker
is aligned with the hinge/tab edge, not the opposite free edge. The whole card
face remains visible, with the uncovered strip at the free edge: 3 mm on the
prototype and 2.5 mm on the definitive card.

## Sticker sheets

Always select a physical variant, rather than manually combining an alphabet
and dimensions:

```sh
# Existing ten-module hardware
python3 V2/Hardware/stickers/generate_stickers.py \
  --variant prototype \
  --output-svg /tmp/demo-64-prototype-50x80.svg

# Matched final hardware
python3 V2/Hardware/stickers/generate_stickers.py \
  --variant definitive \
  --color-preset black-white \
  --output-svg /tmp/international-64-definitive-45x91.svg
```

The sticker generator records the chosen physical variant in its JSON
manufacturing manifest. It rejects an incompatible width or height override.

## Sources and fabrication status

The prototype keeps its 55 × 43 mm planar geometry, drum source and enclosure
reference. The card source is corrected to the measured 0.5 mm substrate; its
enclosure is **not** a validated fabrication source.
To reproduce its 55 mm drum source, pass the explicit old flap width:

```sh
openscad -o /tmp/v2-prototype-drum-55mm.dxf \
  -D 'make3d=false' -D 'part="layout"' -D 'flap_width=55' \
  V2/Hardware/structure/spool.scad
```

The definitive variant is the only current manufacturing route: its card,
64-position drum and two-part enclosure are generated from
`V2/Hardware/mechanical/alphabets_cad/`. Its enclosure still needs a physical
fit check before a production run.

Both card substrates are 0.5 mm. A 0.1 mm sticker is applied to each face,
making the covered area 0.7 mm thick; the opposite free-edge strip, lateral
margins and tab extensions remain bare at 0.5 mm.
