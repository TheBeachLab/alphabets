# Sticker typefaces

The V1 build notes identify **Blue Highway Bold**, by Raymond Larabie, as the
typeface chosen to approximate the original Solari lettering. Existing V2 SVG
files contain only converted vector paths, not reusable font files.

The sticker generator defaults to `BlueHighwayD-International.otf`. It keeps
every glyph available in **Blue Highway D**, the typeface named in the
surviving V2 artwork, and adds only the two glyphs that Blue Highway D lacks:
`ẞ` from Overpass Mono Medium for International 64, and `■` for Demo 64. The
fallback outlines are scaled from Overpass's 2000 UPM to Blue Highway's 1000
UPM; no other Blue Highway glyph is replaced.

Rebuild the hybrid deterministically with:

```sh
python3 V2/Hardware/stickers/fonts/build_blue_highway_international.py
```

[`BlueHighwayD-International.json`](BlueHighwayD-International.json) records
the source hashes, inserted characters and result hash. Blue Highway D is CC0;
the two adapted Overpass glyphs remain under the SIL OFL 1.1, included in
[`LICENSE-OVERPASS-OFL.txt`](LICENSE-OVERPASS-OFL.txt).

`Blue Highway D.otf` is retained because that variant is named by most of the
surviving V2 artwork. `Blue Highway Bd.otf` is retained as the documented V1
choice. Blue Highway D alone lacks `ẞ` and `■`, which is why the derived hybrid
is the default rather than the original file.

`NotoSansMono[wdth,wght].ttf` and `Dream Orphans Bd.otf` remain available as
optional design references; neither is used by the default production output.

The three Blue Highway/Dream Orphans files came from Typodermic's official
public-domain archive and are released under CC0 1.0. See
[LICENSE-CC0.txt](LICENSE-CC0.txt).

| File | SHA-256 |
| --- | --- |
| `OverpassMono-Medium.otf` | `3de6f0d0ecfb7119ef8baa5d866cbbffceb6a573242763500085e2ef78a1b796` |
| `BlueHighwayD-International.otf` | `8cbe442d25882508e20aa9ec90e0f2836bca4c476add400c42ac49425b759f83` |
| `NotoSansMono[wdth,wght].ttf` | `2cb2adb378a8f574213e23df697050b83c54c27df465a2015552740b2769a081` |
| `Blue Highway Bd.otf` | `a5be69737776727b3c5d239c77686a6387b3aea001e7232a50100d5d53e972f7` |
| `Blue Highway D.otf` | `e09e56a5cc4846c87715945f575e743d5585fd5e8fbe99279967f09c8057d718` |
| `Dream Orphans Bd.otf` | `a09f83d10fa1ab0a5f0dd0411e1716c9bef57a8e5a7f81ed3c1ddbbdce6a7424` |
