<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# Alphabets

> [!IMPORTANT]
> **Why V2 has two versions:** V2 Prototype uses the ten existing sticker sets
> printed in Dubai and is available for prototyping while those sets remain in
> service. The expanded DACH and Nordic character map needs more vertical
> artwork space, so V2 Final uses taller stickers and cards together with a
> matched drum and enclosure. V2 Final is the supported target for new batches;
> Prototype support ends when the new Final sticker and card batches are
> available.

> [!WARNING]
> **UNDER HEAVY DEVELOPMENT — NOT READY FOR USE OR FABRICATION.**
> The V2 Final enclosure has a recorded print check, but the complete mechanism,
> Prototype enclosure, electronics and production process are not physically
> validated. Do not order, print, cut or assemble multiple parts without
> checking the dimensions and validating one complete module. V2 Prototype and
> V2 Final are incompatible systems; never mix files between their folders.

![Blender render of ten modular Alphabets V2 split-flap units displaying HALLO WELT!](hallov2.webp)

Welcome to the public repository of the second edition of the worldwide loved **open source split-flap display**. For information about the first release (2014) go [here](V1).

Please also check the [YouTube videos](https://www.youtube.com/playlist?list=PLKDpiLmgp6EuLGCovD-QFxrmyNdrbUmKX)

## What's new
* 120% pure awesomeness.
* 64 cards with international character set.
* Custom colors: Request custom colored modules and custom characters.
* Build your own or order a kit or ready built module.
* No more gears, direct drive motor
* 3D Printed enclosure
* Entirely designed with widely adopted open source software.
* Assemble in multiple layouts of rows and columns.
* Networked electronics: Connect from one to infinite(*) modules together.
* Web based interface: Control your modules interactively with your web browser.

(*) Not really

## TOC

This TOC refers to the V2 Final version

- Mechanical
  - [Cards](doc/cards.md)
  - [Stickers](doc/stickers.md)
  - [Drum](doc/drum.md)
  - [Enclosure](doc/enclosure.md)
- Electronics
  - [Motors](doc/motors.md)
  - [Module Board](doc/module-board.md)
  - [Motherboard](doc/motherboard.md)
  - [Chaining and cables](doc/chaining-and-cables.md)
- Software and Architecture
  - [Protocol](doc/protocol.md)
  - [Module embedded software](doc/module-firmware.md)
  - [Motherboard embedded software](doc/motherboard-firmware.md)
  - [Web interface](doc/web-interface.md)

See the [documentation index](doc/README.md) for the same guide with the
current implementation status of each part.

## License

Except where a file or directory states otherwise, Alphabets' original source
code, firmware, electronics designs, mechanical designs, documentation, and
generated project artifacts are licensed under the [MIT License](LICENSE).
Copyright (c) 2014-2026 [The Beach Lab](https://beachlab.org).

Every commentable file carries a copyright and SPDX license header. JSON,
VS Code workspace, and native KiCad files embed the same fields as document
data so the declaration travels with them. Blender, FreeCAD, OpenType, SVG,
PDF, PNG, JPEG, ZIP, STEP, DXF, binary STL, Gerber, and Excellon files also use
embedded metadata or standard comments and do not need duplicate sidecars.
Only formats without a safely interoperable embedded mechanism use an adjacent
`.license` file. Legacy and bundled third-party sources retain their actual
notices and licenses.
