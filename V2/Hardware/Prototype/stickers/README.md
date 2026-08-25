<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# V2 Prototype stickers

[← Prototype mechanical CAD](../mechanical/README.md) · [Physical variants](../../variants/README.md) · [Shared generator →](../../Final/stickers/README.md)

V2 Prototype uses the **Demo 64** character order and two nominal `50 × 40 mm`
sticker cuts. The cuts are separated by a `1.8 mm` printed gap,
so each uninterrupted cut-aligned artwork cell is `50 × 81.8 mm`. Its colored
background extends `2 mm` past the outer cut lines, producing `54 × 85.8 mm`
background bounds without changing either finished sticker. Each face is
centred on a 55 × 43 mm card, leaving 2.5 mm at each side and an unstickered
3 mm strip at the free edge.

![Demo 64 Prototype sticker sheet](generated/demo-64-black-white-50x80.svg)

## Exact character order

```text
ABCDEFGHIJKLMNOPQRSTUVWXYZ:.0123456789$€&@%×/·#=*+-±()<>,'°■£~©␠
```

There are exactly 64 unique positions. `␠` above denotes the final ASCII space.
This order must match the physical cards and controller mapping.

## Current files

- [`generated/demo-64-black-white-50x80.svg`](generated/demo-64-black-white-50x80.svg): print artwork with cutter guides.
- [`generated/demo-64-black-white-50x80-cut.svg`](generated/demo-64-black-white-50x80-cut.svg): cutter-only vector file.
- [`generated/demo-64-black-white-50x80.pdf`](generated/demo-64-black-white-50x80.pdf): vector PDF.
- [`generated/demo-64-black-white-50x80.json`](generated/demo-64-black-white-50x80.json): dimensions, exact order, font hashes and variant metadata.

[`cut-print/cutprint.svg`](cut-print/cutprint.svg) is the vector source for the
exact Condensed `W` and `%` outlines used by the generator.

## Typeface

`Blue Highway D.otf` is the base font, but it does not contain the Demo‑64 `■`
character. The generated sheet therefore uses the traceable
`BlueHighwayD-International.otf` hybrid, which contains the Blue Highway glyphs
and the square outline from Overpass Mono. `W` uses the Blue Highway Condensed
outline from `cutprint.svg` plus a `0.95902088` horizontal transform. No
installed Condensed font is required.
Hashes and source information are stored beside the font. Overpass is also
kept locally for the enclosure's `α` mark.

Rebuild the sheet from the repository root:

```sh
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --variant prototype \
  --font V2/Hardware/Prototype/stickers/fonts/BlueHighwayD-International.otf \
  --output-svg V2/Hardware/Prototype/stickers/generated/demo-64-black-white-50x80.svg \
  --output-cut-svg V2/Hardware/Prototype/stickers/generated/demo-64-black-white-50x80-cut.svg \
  --output-pdf V2/Hardware/Prototype/stickers/generated/demo-64-black-white-50x80.pdf
```

The shared generator refuses an incomplete font or dimensions that conflict
with the Prototype variant.

[← Prototype mechanical CAD](../mechanical/README.md) · [Physical variants](../../variants/README.md) · [Shared generator →](../../Final/stickers/README.md)
