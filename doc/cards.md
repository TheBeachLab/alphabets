<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# Cards

[← Documentation index](README.md) · [Next: Stickers →](stickers.md)

Each character module contains 64 cards, also called flaps. A card has a front
and a back. When the drum turns, the cards fall one after another and the two
visible halves combine to show one character.

![Cut outline of a V2 Final card](../V2/Hardware/Final/cards/card-50x48-cut.svg)

Prototype uses the ten existing sticker sets printed in Dubai. Final is the
target for new batches and provides the extra card and sticker height required
by the expanded DACH and Nordic character map. Every part in a variant row
below must stay with that variant.

## Two matched card sizes

| Variant | Card body | Including tabs | Sticker on each face | Drum inner width |
| --- | ---: | ---: | ---: | ---: |
| V2 Prototype | 55 × 43 × 0.5 mm | 63 × 43 mm | 50 × 40 × 0.1 mm | 56 mm |
| V2 Final | 50 × 48 × 0.5 mm | 58 × 48 mm | 45 × 45.5 × 0.1 mm | 51 mm |

Both cards are completely visible. The sticker reaches the hinge edge; the
opposite free-edge strip is left unstickered—3 mm on Prototype and 2.5 mm on
Final.

## V2 Final dimensions

| Part | Size |
| --- | ---: |
| Visible card body | 50 × 48 mm |
| Complete width including both tabs | 58 mm |
| Card material | 0.5 mm thick |
| Sticker on each face | 45 × 45.5 mm, 0.1 mm thick |
| Finished covered area | 0.7 mm thick |

The tabs at the top are the pivots. They sit in the drum holes and let the card
rotate. The 45 mm-wide sticker is centred on the 50 mm card, leaving 2.5 mm on
each side. Its edge beside the centre cut faces the tabs.

## Why the dimensions must stay together

The card, sticker, drum, and enclosure form one matched system. Changing the
card width also changes the drum spacing and the required enclosure clearance.
V2 Prototype uses 55 mm cards and is incompatible with the 50 mm V2 Final
system described here.

The [V2 Prototype CadQuery package](../V2/Hardware/Prototype/mechanical/README.md)
generates its 55 × 43 mm card and matched 56 mm drum as one physical profile.

## Design files

- The editable and generated card files are in
  [`V2/Hardware/Final/cards`](../V2/Hardware/Final/cards/README.md).
- The V2 Final CadQuery model is in
  [`V2/Hardware/Final/mechanical`](../V2/Hardware/Final/mechanical/README.md).
- The Prototype card, drum and enclosure are in
  [`V2/Hardware/Prototype/mechanical`](../V2/Hardware/Prototype/mechanical/README.md).
- The exact Prototype/Final match is recorded in
  [`V2/Hardware/variants`](../V2/Hardware/variants/README.md).

> [!CAUTION]
> Make a small fit sample before cutting 64 cards. Material thickness, cutter
> kerf, stickers, and tab clearance all affect whether a card falls freely.

[← Documentation index](README.md) · [Next: Stickers →](stickers.md)
