<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# V2 sticker typeface

The production typeface is `BlueHighwayD-International.otf`, the default used
by the sticker generator. It retains every glyph supplied by **Blue Highway
D** and adds only the two required glyphs it lacks: `ẞ` and `■` from Overpass
Mono Medium. The imported outlines are scaled from Overpass's 2000 UPM to Blue
Highway's 1000 UPM; no available Blue Highway glyph is replaced.

The directory intentionally contains only the files required to generate and
reproduce that production font:

| File | Purpose |
| --- | --- |
| `BlueHighwayD-International.otf` | Production hybrid used for V2 stickers. |
| `BlueHighwayD-International.json` | Source hashes, imported glyphs and output hash. |
| `Blue Highway D.otf` | Primary Blue Highway source. |
| `OverpassMono-Medium.otf` | Source for `ẞ` and `■`. |
| `build_blue_highway_international.py` | Deterministic hybrid-font builder. |
| `LICENSE-CC0.txt` | Blue Highway D licence. |
| `LICENSE-OVERPASS-OFL.txt` | Overpass Mono Medium licence. |

Rebuild the font with:

```sh
python3 V2/Hardware/stickers/fonts/build_blue_highway_international.py
```

The current hashes are retained in
[`BlueHighwayD-International.json`](BlueHighwayD-International.json). Blue
Highway D is released under [CC0 1.0](LICENSE-CC0.txt); the imported Overpass
glyphs remain under [SIL OFL 1.1](LICENSE-OVERPASS-OFL.txt).
