<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# V2 sticker generator

`generate_stickers.py` builds a complete vector sticker sheet from the same
64-position character profile used by the controller. The default output is
the `international-64` profile with white letters on black. Glyphs are written
as vector paths in both SVG and PDF, so the production files do not depend on
fonts installed on the computer or printer.

Install its two Python dependencies once:

```sh
python3 -m pip install -r V2/Hardware/Final/stickers/requirements.txt
```

## V2 Final physical profile

Use the locked Definitivo profile for V2 Final fabrication. See
[`../../variants/`](../../variants/README.md) for the full sticker, card, drum
and enclosure contract.

```sh
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --variant definitive \
  --output-svg /tmp/international-64-definitive-45x91.svg
```

`--variant` fixes the character preset, sticker width, sticker height, cut gap,
and `2 mm` background bleed, and records them in the JSON manifest. It refuses
a conflicting physical override. V2 Prototype fabrication uses the existing
[`../../Prototype/stickers/cut-print/cutprint.svg`](../../Prototype/stickers/cut-print/cutprint.svg)
print-and-cut artwork.

## Print bleed and cutter geometry

The SVG is accompanied by a JSON manufacturing manifest containing the exact
character order, colors, finished cut dimensions, `2 mm` background bleed and
font checksum. The background extends `2 mm` beyond every outer cutter edge,
so a small registration shift cannot expose white material. The artwork also
remains uninterrupted across the intentional center gap while the cutter
geometry contains two independent rectangles. The magenta sticker
outlines are superimposed vector paths in the print SVG and PDF by default,
matching the production file. `--no-guides` produces clean artwork when
required, while `--output-cut-svg` writes the same two-rectangle cutter
geometry as a separate SVG.
Every vector glyph is clipped to its own sticker boundary and uses the non-zero
winding rule in SVG and PDF, avoiding inverted areas where the outlines
overlap. In SVG, the clipping is applied to an outer group in sheet coordinates
so macOS Quick Look renders the transformed glyph paths correctly.

These lines cut the rectangular stickers; they are not the physical flap/card
die. The card die includes the two drum tabs and is generated separately in
[`../cards/`](../cards/README.md).

Every visible character uses one shared **uniform** scale and baseline. The
largest safe uniform scale is selected against both locked sticker dimensions;
no character is squeezed or stretched on one axis. `W` uses the exact Blue
Highway Condensed outline stored in the Prototype `cutprint.svg` source and an
additional `0.95902088` horizontal factor. Each visible outline is geometrically
centered in its equal-sized artwork cell; proportional advance widths do not
change the card size. No glyph receives an individual vertical offset.

The matched **V2 Definitivo** geometry uses two `45 × 45.5 mm` cuts separated
by a `1.8 mm` printed gap. The locked cut width remains `45 mm`; the complete
cut-aligned artwork cell is therefore `45 × 92.8 mm`, while its colored
background bounds are `49 × 96.8 mm` after the `2 mm` bleed on every outer
side. Each sticker is centred laterally on the complete
`50 × 48 mm` visible face and aligned to its hinge/tab edge. The opposite
2.5 mm strip remains unstickered. The center-cut edge of each half is the edge
that must face the tabs. Skipping the `1.8 mm` printed interval between the two
cuts compensates the physical separation and preserves continuous curves and
diagonal strokes. Generate it without changing the shared alignment with:

```sh
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --variant definitive \
  --output-svg /tmp/international-45x91.svg \
  --output-cut-svg /tmp/international-45x91-cut.svg \
  --output-pdf /tmp/international-45x91.pdf
```

`--horizontal-padding` and `--vertical-padding` reduce the safe area available
to the uniform scale; neither option deforms the type. Generic experiments can
override the background extension with `--bleed`, but physical variants lock
it to their declared manufacturing value.

The matching card cutter and 51 mm drum separation are documented in
[`../cards/`](../cards/README.md).

## Color presets

| Preset | Background | Letters |
| --- | --- | --- |
| `black-white` (default) | black | white |
| `black-yellow` | black | yellow |
| `yellow-black` | yellow | black |
| `white-black` | white | black |

Select one with, for example, `--color-preset yellow-black`. Any preset can be
overridden with exact RGB values:

```sh
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --background '#14213D' --foreground '#FCA311' \
  --output-svg /tmp/my-stickers.svg --output-pdf /tmp/my-stickers.pdf
```

Colors use `#RRGGBB`. Yellow is `#FFCC00`.

Generate the four production color variants at 45 × 91 mm with:

```sh
for preset in black-white black-yellow yellow-black white-black; do
  python3 V2/Hardware/Final/stickers/generate_stickers.py \
    --variant definitive \
    --color-preset "$preset" \
    --output-svg "V2/Hardware/Final/stickers/generated/international-64-${preset}-45x91.svg" \
    --output-pdf "V2/Hardware/Final/stickers/output/pdf/alphabets-international-64-${preset}-45x91-stickers.pdf"
done

# The cutter geometry is color-independent, so one current cut file is enough.
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --variant definitive \
  --color-preset black-white \
  --output-svg /tmp/international-64-black-white-45x91.svg \
  --output-cut-svg V2/Hardware/Final/stickers/generated/international-64-black-white-45x91-cut.svg
```

These commands produce the complete current `45x91` Final artifact set.

## Preset or custom characters

A `--preset` or settings file remains available for non-fabrication
experiments:

```sh
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --settings V2/Hardware/Final/stickers/settings.example.json \
  --output-svg /tmp/custom-stickers.svg
```

Custom profiles must pass the shared validation: exactly 64 unique printable
characters and exactly one ASCII space. The generator stops before writing
production files if any selected font cannot render a required character.

## Typeface

The generator uses the traceable **BlueHighwayD-International** hybrid. It
contains the Blue Highway D outlines and supplies the two characters missing
from that source through documented fallbacks. The Final profile uses the exact
Blue Highway Condensed W outline stored in the Prototype `cutprint.svg`
fabrication file.
International 64 also uses the Condensed Æ outline
from Typodermic's official
[CC0 Blue Highway package](https://typodermicfonts.com/public-domain/). Its
final horizontal factor makes its visible width exactly match the transformed
W. The Final profile also uses the exact condensed `%` outline stored in
Prototype `cutprint.svg`. No locally installed font is required for these
overrides.

The alignment model follows the lesson from Scott Bezek's production
[splitflap generator](https://github.com/scottbez1/splitflap/blob/master/3d/flap_fonts.scad):
font scale and position are explicit manufacturing parameters. This generator
uses one global uniform base scale and baseline for the entire profile, with
each font outline centered inside the common physical card. The documented W
and Æ horizontal factors are applied after that base scale. Exact provenance
and checksums are recorded in [`fonts/`](fonts/README.md).

Choose another OpenType font with `--font path/to/font.otf`. For a variable
font, select its weight and width with `--font-weight 600 --font-width 80`.
The generator rejects the font unless that single file covers every selected
character. The manifest records the resolved file, variation, spacing model,
shared baseline/scale, advance range and SHA-256 checksum.
