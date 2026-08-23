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
python3 -m pip install -r V2/Hardware/stickers/requirements.txt
```

## Physical variants

The generator can lock characters and sticker dimensions to a physical V2
variant. This is the normal fabrication path; use the complete
[`V2/Prototype`](../../Prototype/README.md) or
[`V2/Final`](../../Final/README.md) package so the artwork cannot be mixed with
the wrong card, drum or enclosure.

```sh
# Existing 55 mm demonstration hardware; 2.5 mm side margin.
python3 V2/Hardware/stickers/generate_stickers.py \
  --variant prototype \
  --output-svg /tmp/demo-64-prototype-50x80.svg

# Matched 50 mm definitive hardware; the same 2.5 mm side margin.
python3 V2/Hardware/stickers/generate_stickers.py \
  --variant definitive \
  --output-svg /tmp/international-64-definitive-45x91.svg
```

`--variant` fixes the character preset, sticker width and sticker height, and
records the variant in the JSON manifest. It refuses a conflicting width or
height override. The prototype sticker is nominally `50 × 80 mm`, split at
40 mm. The body itself remains visible across its complete 43 mm height; the
40 mm half is placed from `y=3` to `y=43 mm`, aligned with the hinge/tab edge.
The opposite `y=0…3 mm` strip remains visible but unstickered.

In the preserved `cut-print/cutprint.svg`, each historical magenta cutter
rectangle is about `51.0 × 40.1 mm` (`192.756 × 151.570` SVG px at 96 dpi).
That is the cutter allowance around the nominal `50 × 40 mm` prototype
sticker, not evidence of a 43 mm-high sticker.

## Generic legacy sheet

This mode is for experiments only: it is not associated with either physical
variant and must not be sent to fabrication.

From the repository root:

```sh
python3 V2/Hardware/stickers/generate_stickers.py \
  --output-svg /tmp/international-64-generic-55x86.svg \
  --output-cut-svg /tmp/international-64-generic-55x86-cut.svg \
  --output-pdf /tmp/international-64-generic-55x86.pdf
```

The SVG is accompanied by a JSON manufacturing manifest containing the exact
character order, colors, card/page dimensions and font checksum. Card size is
55 × 86 mm with the flap cut at 43 mm. The default 22-column layout is
1388 × 278 mm, matching the limits of the surviving production sheet. The
center cut passes through the uninterrupted character: the generator does not
remove a strip from the artwork. The magenta sticker outlines and center cuts are
superimposed vector paths in the print SVG and PDF by default, matching the
production file. `--no-guides` produces clean artwork when required, while
`--output-cut-svg` also writes the same cutter geometry as a separate SVG.
Every vector glyph is clipped to its own sticker boundary and uses the non-zero
winding rule in SVG and PDF, avoiding inverted areas where the outlines
overlap. In SVG, the clipping is applied to an outer group in sheet coordinates
so macOS Quick Look renders the transformed glyph paths correctly.

These lines cut the rectangular stickers; they are not the physical flap/card
die. The card die includes the two drum tabs and is generated separately in
[`../cards/`](../cards/README.md).

Every visible character uses one shared horizontal scale, vertical scale and
baseline. The two scales are calculated once from the widest and tallest glyph
in the selected 64-position profile. This global transform gives the complete
set the tall, narrow proportion of Blue Highway D without per-character
distortion. Each visible outline is geometrically centered in its equal-sized
card; proportional advance widths do not change the card size. No glyph
receives an individual scale or vertical offset.

The matched **V2 Final** geometry is `45 × 91 mm`: after the center cut it
creates two `45 × 45.5 mm` stickers. Each is centred laterally on the complete
`50 × 48 mm` visible face and aligned to its hinge/tab edge. The opposite
2.5 mm strip remains unstickered. The center-cut edge of each half is the edge
that must face the tabs; this preserves continuous curves and diagonal strokes
without a visual jump. Generate it without changing the shared alignment with:

```sh
python3 V2/Hardware/stickers/generate_stickers.py \
  --variant definitive \
  --output-svg /tmp/international-45x91.svg \
  --output-cut-svg /tmp/international-45x91-cut.svg \
  --output-pdf /tmp/international-45x91.pdf
```

`--horizontal-padding` and `--vertical-padding` control the guaranteed clear
area. Increasing either value reduces the entire type system uniformly.
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
python3 V2/Hardware/stickers/generate_stickers.py \
  --background '#14213D' --foreground '#FCA311' \
  --output-svg /tmp/my-stickers.svg --output-pdf /tmp/my-stickers.pdf
```

Colors use `#RRGGBB`. Yellow is the historical `#FFCC00`.

Generate all four colors in the correct version folder with:

```sh
cd V2/Prototype  # or V2/Final
make stickers
```

## Preset or custom characters

Use `--variant prototype` for the ten existing demo drums. A `--preset` or
settings file remains available for non-fabrication experiments:

```sh
python3 V2/Hardware/stickers/generate_stickers.py \
  --settings V2/Code/settings.example.json \
  --output-svg /tmp/custom-stickers.svg
```

Custom profiles must pass the shared validation: exactly 64 unique printable
characters and exactly one ASCII space. The generator stops before writing
production files if any selected font cannot render a required character.

## Typeface

The generator uses **Overpass Mono Medium** at weight 500. Blue Highway and
Overpass both derive from FHWA/Highway Gothic road-sign lettering, while the
mono variant keeps every drum position on a common advance. It provides the
full `international-64` and `demo-64` coverage in one font, including `ẞ` and
`■`. The bundled OTF is the unmodified official release from the
[Red Hat Overpass repository](https://github.com/RedHatOfficial/Overpass) and
is distributed under the SIL Open Font License 1.1.

The alignment model follows the lesson from Scott Bezek's production
[splitflap generator](https://github.com/scottbez1/splitflap/blob/master/3d/flap_fonts.scad):
font scale and position are explicit manufacturing parameters. This generator
uses one global x/y transform and baseline for the entire profile, with each
font outline centered inside the common physical card. Exact provenance and
checksums are recorded in [`fonts/`](fonts/README.md).

Choose another OpenType font with `--font path/to/font.otf`. For a variable
font, select its weight and width with `--font-weight 600 --font-width 80`.
The generator rejects the font unless that single file covers every selected
character. The manifest records the resolved file, variation, spacing model,
shared baseline/scale, advance range and SHA-256 checksum.
