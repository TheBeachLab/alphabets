# V2 physical variants

`variants.json` is the authoritative contract that prevents parts from the two
incompatible V2 builds being mixed. A character order is inseparable from its
sticker sheet, card, drum spacing and enclosure source.

| Variant | Character preset | Sticker / halves | Card | Drum inner / outer width | Enclosure |
| --- | --- | --- | --- | --- | --- |
| **V2 Prototipo** | `demo-64` | 55 × 86 / 55 × 43 mm | 55 × 43 mm, 55 × 40 visible | 56 / 60.3 mm | historical FreeCAD reference only |
| **V2 Definitivo** | `international-64` | 50 × 96 / 50 × 48 mm | 50 × 48 mm, 50 × 45.5 visible | 51 / 55.3 mm | current two-piece, open-rear CadQuery source |

The 50 × 86 mm sticker is an abandoned transition, not a physical variant. Do
not use it to make cards, drums or enclosures.

## Sticker sheets

Always select a physical variant, rather than manually combining an alphabet
and dimensions:

```sh
# Existing ten-module hardware
python3 V2/Hardware/stickers/generate_stickers.py \
  --variant prototype \
  --output-svg /tmp/demo-64-prototype-55x86.svg

# Matched final hardware
python3 V2/Hardware/stickers/generate_stickers.py \
  --variant definitive \
  --color-preset black-white \
  --output-svg /tmp/international-64-definitive-50x96.svg
```

The sticker generator records the chosen physical variant in its JSON
manufacturing manifest. It rejects an incompatible width or height override.

## Sources and fabrication status

The prototype is preserved, not retroactively redesigned. Its original card,
drum source and enclosure reference remain in the paths listed in
`variants.json`. Its enclosure is **not** a validated fabrication source.
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
