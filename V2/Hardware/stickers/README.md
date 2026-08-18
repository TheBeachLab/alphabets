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

## Default sheet

From the repository root:

```sh
python3 V2/Hardware/stickers/generate_stickers.py \
  --output-svg V2/Hardware/stickers/generated/international-64-black-white.svg \
  --output-cut-svg V2/Hardware/stickers/generated/international-64-black-white-cut.svg \
  --output-pdf output/pdf/alphabets-international-64-black-white-stickers.pdf
```

The SVG is accompanied by a JSON manufacturing manifest containing the exact
character order, colors, card/page dimensions and font checksum. Card size is
55 × 86 mm with the flap cut at 43 mm. The default 22-column layout is
1388 × 278 mm, matching the limits of the surviving production sheet. The
center cut passes through the uninterrupted character: the generator does not
remove a strip from the artwork. Print files are clean by default; the cutter
geometry is written separately with `--output-cut-svg`, so lines never cover or
visually merge with the letters. `--guides` is available only for an overlaid
alignment proof. Every vector glyph is also clipped to its own card boundary
and uses the TrueType non-zero winding rule in SVG and PDF, avoiding inverted
areas where the outlines overlap.

Every visible character uses one shared typographic scale, monospaced advance
and baseline. The scale is calculated once from the widest and tallest glyph
in the selected 64-position profile. If an accent needs more vertical room,
the complete profile becomes slightly smaller and gains equal top/bottom
clearance; individual glyphs are never shifted or resized.

The physical default remains the existing `55 × 86 mm`. A taller, narrower
comparison can be generated without changing the shared alignment:

```sh
python3 V2/Hardware/stickers/generate_stickers.py \
  --card-width 50 --card-height 96 \
  --output-svg /tmp/international-50x96.svg \
  --output-cut-svg /tmp/international-50x96-cut.svg \
  --output-pdf /tmp/international-50x96.pdf
```

`--horizontal-padding` and `--vertical-padding` control the guaranteed clear
area. Increasing either value reduces the entire type system uniformly.

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

## Preset or custom characters

Use `--preset demo-64` for the ten existing demo drums, or pass the same
settings file used by the software:

```sh
python3 V2/Hardware/stickers/generate_stickers.py \
  --settings V2/Code/settings.example.json \
  --output-svg /tmp/custom-stickers.svg
```

Custom profiles must pass the shared validation: exactly 64 unique printable
characters and exactly one ASCII space. The generator stops before writing
production files if any selected font cannot render a required character.

## Typeface

The project history names Blue Highway Bold as the selected Solari-like
typeface, but the available Blue Highway files do not contain uppercase `ẞ`
and are proportional. The generator therefore uses **Noto Sans Mono** at
weight 700 and width 100. This single monospaced font contains every
character in both `international-64` and `demo-64`, including `ẞ` and `■`.
It is distributed under the SIL Open Font License 1.1 from the
[official Google Fonts repository](https://github.com/google/fonts/tree/main/ofl/notosansmono).

The alignment model follows the lesson from Scott Bezek's production
[splitflap generator](https://github.com/scottbez1/splitflap/blob/master/3d/flap_fonts.scad):
font scale and position are explicit manufacturing parameters. This generator
uses the stricter option requested here—one scale, advance and baseline for
the entire profile, rather than per-character overrides. Exact provenance and
checksums are recorded in [`fonts/`](fonts/README.md).

Choose another OpenType font with `--font path/to/font.otf`. For a variable
font, select its weight and width with `--font-weight 600 --font-width 80`.
The generator rejects the font unless that single file covers every selected
character with one common advance. The manifest records the resolved file,
variation, shared baseline/scale/advance and SHA-256 checksum.
