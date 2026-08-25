<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# V2 physical variants

`variants.json` is the authoritative contract that prevents parts from the two
incompatible V2 builds being mixed. A character order is inseparable from its
sticker sheet, card, drum spacing and enclosure source.

| Variant | Character preset | Sticker / halves | Card | Drum inner / outer width | Enclosure |
| --- | --- | --- | --- | --- | --- |
| **V2 Prototipo** | `demo-64` | two 50 × 40 mm cuts, 1.8 mm gap | 55 × 43 mm, all visible | 56 / 60.3 mm | isolated CadQuery Prototype derivative; physical fit pending |
| **V2 Definitivo** | `international-64` | two 45 × 45.5 mm cuts, 1.8 mm gap | 50 × 48 mm, all visible | 51 / 55.3 mm | current two-piece, open-rear CadQuery source |

Both variants leave a 2.5 mm placement margin at each lateral edge. The sticker
is aligned with the hinge/tab edge, not the opposite free edge. The whole card
face remains visible, with the uncovered strip at the free edge: 3 mm on the
prototype and 2.5 mm on the definitive card.

The `1.8 mm` center gap is part of the printed artwork layout, not a third
sticker. The artwork remains continuous through it, while the cutter receives
two independent half-card rectangles. Typography uses one width-driven uniform
base scale so the widest glyph reaches the locked sticker width. W uses the
exact historical Prototype Blue Highway Condensed outline with horizontal
factor `0.95902088`. International 64 uses the actual Condensed Æ outline and
a small width adjustment so its final visible width exactly matches W.

## Sticker sheets

Always select a physical variant, rather than manually combining an alphabet
and dimensions:

```sh
# Existing ten-module hardware
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --variant prototype \
  --output-svg /tmp/demo-64-prototype-50x80.svg

# Matched final hardware
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --variant definitive \
  --color-preset black-white \
  --output-svg /tmp/international-64-definitive-45x91.svg
```

The sticker generator records the chosen physical variant in its JSON
manufacturing manifest. It rejects an incompatible width or height override.

## Sources and fabrication status

The prototype now has an isolated CadQuery package under
[`../Prototype/mechanical`](../Prototype/mechanical/README.md). It was copied
from the trusted printed Final source and adjusted as one matched profile: card,
stickers, drum, pawl and enclosure. Its enclosure uses the settled Final
transforms as a conservative reference and is **not yet physically validated
as a Prototype enclosure**.

Rebuild the Prototype package with:

```sh
cd V2/Hardware/Prototype/mechanical
make check
```

The definitive variant remains the only one confirmed against a current
physical print. Its card and 64-position drum are generated from
`V2/Hardware/Final/mechanical/alphabets_cad/`, and its sole current enclosure is
the capture-fitted pipeline under
`generated/captured-enclosure/`, confirmed against the latest physical print
on 2026-08-23. Further fit observations are still required before a production
run.

Both card substrates are 0.5 mm. A 0.1 mm sticker is applied to each face,
making the covered area 0.7 mm thick; the opposite free-edge strip, lateral
margins and tab extensions remain bare at 0.5 mm.
