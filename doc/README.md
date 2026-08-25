<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# Alphabets V2 guide

[← Project README](../README.md) · [Start with the cards →](cards.md)

This guide explains **V2 Final** in the order that information moves through
the display: a message enters the controller, travels through the module
chain, and each module turns its drum until the requested card is visible.

V2 Prototype exists to use the ten sticker sets printed in Dubai during
prototyping. The expanded DACH and Nordic character map needs more vertical
artwork space, so V2 Final uses matched taller stickers, cards, drum and
enclosure. Final is the supported target for new batches; Prototype support
ends when new Final sticker and card batches are available. The
[physical variants contract](../V2/Hardware/variants/README.md) records the
exact dimensions and files that belong together.

> [!WARNING]
> V2 is under development. The V2 Final enclosure has a recorded print check,
> but the complete mechanism, Prototype enclosure, electronics and production
> process are not physically validated. Make fit samples and validate one
> complete module before ordering multiple parts.

## Mechanical

1. [Cards](cards.md) — the 64 moving flaps that carry the characters.
2. [Stickers](stickers.md) — the printed character artwork applied to the cards.
3. [Drum](drum.md) — the rotating structure that holds the cards in order.
4. [Enclosure](enclosure.md) — the two-part body around one complete module.

## Electronics

1. [Motors](motors.md) — how one motor advances one drum.
2. [Module board](module-board.md) — the small controller fitted to each module.
3. [Motherboard](motherboard.md) — the planned controller for the complete display.
4. [Chaining and cables](chaining-and-cables.md) — the six-wire ring between boards.

## Software and architecture

1. [Protocol](protocol.md) — the two communication layers and what they carry.
2. [Module embedded software](module-firmware.md) — firmware that moves and homes one drum.
3. [Motherboard embedded software](motherboard-firmware.md) — planned layout and chain control.
4. [Web interface](web-interface.md) — planned user interface for sending text.

## What is implemented now?

| Area | Current repository status |
| --- | --- |
| Cards, stickers, drum, enclosure | Matched Prototype and Final sources and manufacturing exports exist; complete physical validation is still required |
| Motor | A 28BYJ-48 reference model and firmware defaults exist; the real assembly still needs validation |
| Module board | Editable ATtiny1624 KiCad design and fabrication exports exist |
| Module firmware | ATtiny1624 firmware and host-side tests exist |
| Motherboard hardware and firmware | Protocol responsibilities are defined; implementation is not in the repository yet |
| Web interface | Message protocol is defined; implementation is not in the repository yet |

V2 Prototype and V2 Final parts must never be mixed.
