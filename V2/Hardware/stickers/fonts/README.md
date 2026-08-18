# Sticker typefaces

The V1 build notes identify **Blue Highway Bold**, by Raymond Larabie, as the
typeface chosen to approximate the original Solari lettering. Existing V2 SVG
files contain only converted vector paths, not reusable font files.

The sticker generator defaults to `NotoSansMono[wdth,wght].ttf` at weight 700
and width 100. It covers both complete 64-position profiles—including `ẞ` and
`■`—with one monospaced advance; the generator never mixes typefaces or moves
individual glyph baselines. This is the unmodified variable font from the
official Google Fonts repository, licensed under OFL 1.1. See
[`LICENSE-OFL.txt`](LICENSE-OFL.txt).

`Blue Highway D.otf` is retained because that variant is named by most of the
surviving V2 artwork. `Blue Highway Bd.otf` is retained as the documented V1
choice. Neither is valid by itself for `international-64`, because both lack
`ẞ`. They are retained as historical design references, not as defaults for
the strictly aligned generator.

`Dream Orphans Bd.otf` has complete `international-64` glyph coverage, but is
proportional; it is also retained only as a design reference because it cannot
provide the required common advance.

The three Blue Highway/Dream Orphans files came from Typodermic's official
public-domain archive and are released under CC0 1.0. See
[LICENSE-CC0.txt](LICENSE-CC0.txt).

| File | SHA-256 |
| --- | --- |
| `NotoSansMono[wdth,wght].ttf` | `2cb2adb378a8f574213e23df697050b83c54c27df465a2015552740b2769a081` |
| `Blue Highway Bd.otf` | `a5be69737776727b3c5d239c77686a6387b3aea001e7232a50100d5d53e972f7` |
| `Blue Highway D.otf` | `e09e56a5cc4846c87715945f575e743d5585fd5e8fbe99279967f09c8057d718` |
| `Dream Orphans Bd.otf` | `a09f83d10fa1ab0a5f0dd0411e1716c9bef57a8e5a7f81ed3c1ddbbdce6a7424` |
