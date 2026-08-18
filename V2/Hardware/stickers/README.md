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
  --output-pdf output/pdf/alphabets-international-64-black-white-stickers.pdf
```

The SVG is accompanied by a JSON manufacturing manifest containing the exact
character order, colors, card/page dimensions, font checksums and font used for
each position. Card size is 55 × 86 mm with the flap split at 43 mm. Magenta
cut guides are included by default and can be omitted with `--no-guides`.

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
typeface. Most surviving V2 artwork identifies `Blue Highway D`, so that is the
generator default. The current Blue Highway fonts do not contain uppercase
`ẞ`; the generator uses the bundled Dream Orphans Bold only for that glyph.
Both families are by Raymond Larabie and were obtained from Typodermic's
[official public-domain collection](https://typodermicfonts.com/public-domain/).
Exact provenance and checksums are recorded in [`fonts/`](fonts/README.md).

Choose another OpenType font with `--font path/to/font.otf`; repeat
`--fallback-font path/to/fallback.otf` when required. The manifest records the
resolved files and SHA-256 checksums.
