<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->

# V2 Prototype — 55 mm

This folder is the only entry point for the existing physical prototype. Do
not combine its parts with `V2/Final`.

| Part | Prototype dimension |
| --- | --- |
| Card body | 55 × 43 × 0.5 mm |
| Card including tabs | 63 mm wide |
| Sticker sheet cell | 50 × 80 mm, split at 40 mm |
| Drum | 56 mm inner / 60.3 mm outer width |
| Character preset | `demo-64` |

`design.toml` is the parametric profile. `variant.json` is the physical
contract. `generated/` contains the matched cards, stickers, drum, Blender
gravity scene and enclosure; every one of those outputs is prototype-only.
`source/` preserves the earlier FreeCAD and cutter files for comparison; the
current manufacturing exports are always under `generated/`.

Build and validate the complete package:

```sh
cd V2/Prototype
make setup
make all
make check
```

Known unresolved issue: the nominal 3 × 0.5 mm tab corner radius is 1.5207 mm,
which interferes by 0.0207 mm with a nominal Ø3 mm drum hole. The source keeps
that measured legacy geometry visible; it is not evidence of fabrication fit.
