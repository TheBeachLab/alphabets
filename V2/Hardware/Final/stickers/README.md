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

## Physical variants

The generator can lock characters and sticker dimensions to a physical V2
variant. This is the normal fabrication path; see
[`../../variants/`](../../variants/README.md) for the full card, drum and
enclosure contract.

```sh
# Existing 55 mm demonstration hardware; 2.5 mm side margin.
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --variant prototype \
  --output-svg /tmp/demo-64-prototype-50x80.svg

# Matched 50 mm definitive hardware; the same 2.5 mm side margin.
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --variant definitive \
  --output-svg /tmp/international-64-definitive-45x91.svg
```

`--variant` fixes the character preset, sticker width and sticker height, and
records the variant in the JSON manifest. It refuses a conflicting width or
height override. The prototype has two nominal `50 × 40 mm` cuts separated by
a `1.8 mm` printed gap. The body itself remains visible across its complete
43 mm height; the
40 mm half is placed from `y=3` to `y=43 mm`, aligned with the hinge/tab edge.
The opposite `y=0…3 mm` strip remains visible but unstickered.

In the preserved `cut-print/cutprint.svg`, each historical magenta cutter
rectangle is about `51.0 × 40.1 mm` (`192.756 × 151.570` SVG px at 96 dpi).
That is the cutter allowance around the nominal `50 × 40 mm` prototype
sticker, not evidence of a 43 mm-high sticker. Its measured center gap is
approximately `1.794 mm`; the variant contract rounds this to `1.8 mm`.

## Generic legacy sheet

This mode is for experiments only: it is not associated with either physical
variant and must not be sent to fabrication.

From the repository root:

```sh
python3 V2/Hardware/Final/stickers/generate_stickers.py \
  --output-svg /tmp/international-64-generic-55x86.svg \
  --output-cut-svg /tmp/international-64-generic-55x86-cut.svg \
  --output-pdf /tmp/international-64-generic-55x86.pdf
```

The SVG is accompanied by a JSON manufacturing manifest containing the exact
character order, colors, card/page dimensions and font checksum. Card size is
55 × 86 mm with the flap cut at 43 mm. The default 22-column layout is
1388 × 278 mm, matching the limits of the surviving production sheet. The
artwork remains uninterrupted across the intentional center gap while the
cutter geometry contains two independent rectangles. The magenta sticker
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
no character is squeezed or stretched on one axis. The sole
historical exception currently reproduced is `W`: it uses the exact Blue
Highway Condensed outline recovered from the Prototype artwork and its
additional `0.95902088` horizontal factor. Each visible outline is geometrically
centered in its equal-sized artwork cell; proportional advance widths do not
change the card size. No glyph receives an individual vertical offset.

The matched **V2 Definitivo** geometry uses two `45 × 45.5 mm` cuts separated
by a `1.8 mm` printed gap. The locked cut width remains `45 mm`; the complete
artwork cell is therefore `45 × 92.8 mm`. Each sticker is centred laterally on the complete
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

`--horizontal-padding` reduces the width available to the uniform scale.
`--vertical-padding` is a validation clearance: it never rescales or deforms
the type, and generation stops if the width-driven artwork is too tall.
The matching card cutter and 51 mm drum separation are documented in
[`../cards/`](../cards/README.md). Use `--variant prototype` for the existing
55 mm cards with nominal `50 × 40 mm` stickers / Demo 64 hardware.

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

Colors use `#RRGGBB`. Yellow is the historical `#FFCC00`.

Generate the four production color variants at 45 × 91 mm with:

```sh
for preset in black-white black-yellow yellow-black white-black; do
  python3 V2/Hardware/Final/stickers/generate_stickers.py \
    --variant definitive \
    --color-preset "$preset" \
    --output-svg "V2/Hardware/Final/stickers/generated/international-64-${preset}-45x91.svg" \
    --output-pdf "V2/Hardware/Final/stickers/output/pdf/alphabets-international-64-${preset}-45x91-stickers.pdf"
done
```

## Preset or custom characters

Use `--variant prototype` for the ten existing demo drums. A `--preset` or
settings file remains available for non-fabrication experiments:

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
preserves the Blue Highway D outlines and supplies the two characters missing
from that source through documented fallbacks. The physical profiles replace
W with the exact Blue Highway Condensed outline recovered from the historical
Prototype artwork. International 64 also uses the actual Condensed Æ outline
from Typodermic's official
[CC0 Blue Highway package](https://typodermicfonts.com/public-domain/). Its
final horizontal factor makes its visible width exactly match the transformed
W. Both physical profiles use the exact condensed `%` outline recovered from
the historical Prototype artwork. No locally installed font is required for
these overrides.

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
