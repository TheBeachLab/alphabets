<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->

# V2 Final — 50 mm

This folder is the only entry point for the final/international physical
design. Do not combine its parts with `V2/Prototype`.

| Part | Final dimension |
| --- | --- |
| Card body | 50 × 48 × 0.5 mm |
| Card including tabs | 58 mm wide |
| Sticker sheet cell | 45 × 91 mm, split at 45.5 mm |
| Drum | 51 mm inner / 55.3 mm outer width |
| Character preset | `international-64` |

`design.toml` is the parametric profile. `variant.json` is the physical
contract. `generated/` contains the matched cards, stickers, drum, Blender
gravity scene and enclosure; every one of those outputs is final-only.
`source/` preserves the earlier FreeCAD and cutter files for comparison; the
current manufacturing exports are always under `generated/`.

Build and validate the complete package:

```sh
cd V2/Final
make setup
make all
make check
```
