<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->

# Shared V2 card generator

`generate_card.py` produces the editable FreeCAD card, SVG/DXF cutter outlines
and a manufacturing manifest. It is shared by two incompatible complete
packages:

| Version | Card body | Tabs | Drum inner / outer width |
| --- | --- | --- | --- |
| [`V2/Prototype`](../../Prototype/README.md) | 55 × 43 × 0.5 mm | 4 × 3 mm | 56 / 60.3 mm |
| [`V2/Final`](../../Final/README.md) | 50 × 48 × 0.5 mm | 4 × 2.5 mm | 51 / 55.3 mm |

The complete visible face includes the tab band. A 0.1 mm sticker is applied to
each face, so a finished stickered card is 0.7 mm thick. The substrate is black;
the visible color comes from the sticker.

Use the version-level build so the card is generated together with matching
stickers, drum, Blender capture and enclosure:

```sh
cd V2/Prototype  # or V2/Final
make cards
make check
```

The FreeCAD file embeds the variant, exact dimensions and project licence.
Prototype and Final outputs live only below their respective `generated/cards`
folders.
