<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->

# Shared Blender gravity generator

This directory turns either complete CadQuery profile into a rigid-body review
scene. It is shared tooling: generated scenes belong in
[`V2/Prototype`](../../Prototype/README.md) or
[`V2/Final`](../../Final/README.md), never in a mixed common output folder.

Build the selected version through its own entry point:

```sh
cd V2/Prototype  # or V2/Final
make setup
make blender
make enclosure
make check
```

Each scene contains the selected drum, 64 solid rigid cards, 64 hinge
constraints, 128 sticker faces, the fixed pawl and the captured floor. The
sticker faces share a packed atlas. `sticker-mapping.json` records the physical
variant, character, face and UV orientation; the lower/front artwork is
horizontally flipped so it reads correctly after turning.

The scene releases and settles the cards under gravity before writing
`cards-position-capture.json`. That capture contains the physical variant and
is the only capture accepted by the corresponding enclosure export. The
version-level check rejects a Prototype capture in a Final enclosure, or the
reverse.

CadQuery remains the manufacturing source. Blender is used only to inspect
movement and capture the occupied card volume. A plausible simulation is not
physical fit validation.

## Interactive stepping

Open the generated `.blend` in its version folder. The `Alphabets` sidebar
advances the motor-driven drum by exact 64-position steps. Both drum sides,
supports, shaft and card hinge axes move with it while the cards remain
independent rigid bodies. The long timeline is configured to stop rather than
loop, allowing several revolutions before capturing a settled state.

The scene uses increased Bullet substeps and solver iterations to reduce thin
card tunnelling. Blender still approximates contacts, so any enclosure intended
for fabrication must retain measured clearance and be checked with the real
drum.

## Presentation wall

The existing HALLO/WELT wall scripts are a Final-profile presentation workflow,
not a fabrication package. They remain shared source until they are separately
parameterized; they must not be used as evidence that a Prototype enclosure
fits.
