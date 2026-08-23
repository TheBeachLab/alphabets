<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# Enclosure

[← Drum](drum.md) · [Documentation index](README.md) · [Next: Motors →](motors.md)

The enclosure is the body around one drum. It keeps neighbouring modules
aligned, supports the motor and shaft, carries the electronics, and leaves the
front open so the character can be seen.

![Current capture-fitted V2 Final enclosure](../V2/Hardware/Final/mechanical/generated/captured-enclosure/preview/captured-enclosure-module.svg)

## Current V2 Final design

The enclosure is a two-part CadQuery model with an open front and rear. The
opening makes it possible to load cards, route wires, and service the mechanism.
The current model also includes:

- motor-side and shaft-side supports;
- space for the module electronics;
- alignment features for arranging modules in rows and columns;
- a separate front pawl;
- upper and lower printed parts.

The geometry is built around the saved settled card positions, not only around
the 85 mm drum circle. That extra moving envelope matters because cards extend
beyond the drum while they flip. This capture-fitted model is the enclosure
shown in the VS Code OCP viewer and is the only current enclosure source. The
latest physical print was confirmed from this version on 2026-08-23.

## Files

- The editable source, parameters, commands, and validation notes are in the
  [mechanical README](../V2/Hardware/Final/mechanical/README.md).
- Printable STL, neutral STEP, the review SVG, and their manifest are all under
  [`generated/captured-enclosure`](../V2/Hardware/Final/mechanical/generated/captured-enclosure/).
- The four-part A1 Mini print plate used by this pipeline is
  [`captured-enclosure-bambu-a1-mini-four-part-plate.stl`](../V2/Hardware/Final/mechanical/generated/captured-enclosure/print/captured-enclosure-bambu-a1-mini-four-part-plate.stl).

The similarly named enclosure files that used to live directly under
`generated/preview`, `generated/print`, and `generated/step` belonged to an
older parallel model. They have been retired so they cannot be confused with
the printed capture-fitted enclosure.

> [!WARNING]
> The enclosure is still a printable prototype. Test one complete module with
> the real drum, cards, motor, shaft, pawl, magnets, and cables before printing
> an array.

[← Drum](drum.md) · [Documentation index](README.md) · [Next: Motors →](motors.md)
