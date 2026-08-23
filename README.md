<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# Alphabets

> [!WARNING]
> **UNDER HEAVY DEVELOPMENT — NOT READY FOR USE OR FABRICATION.**
> The mechanical designs, electronics and generated manufacturing files are
> being actively revised and have not been physically validated. Do not order,
> print, cut or assemble parts from this repository without independently
> checking every dimension. V2 Prototype and V2 Final are incompatible systems;
> never mix files between their folders.

<p align="center">
  <img src="hero-fashion-window.jpg" width="49%" alt="Alphabets split-flap strip in a fashion storefront at blue hour">
  <img src="hero-cafe.jpg" width="49%" alt="Alphabets split-flap matrix receiving a message inside a cafe">
</p>

![Blender render of ten modular Alphabets V2 split-flap units displaying HALLO WELT!](hallov2.webp)

Welcome to the public repository of the second edition of the worldwide loved **open source split-flap display**. Please find information about the first release [here](V1).

Please also check the [YouTube videos](https://www.youtube.com/playlist?list=PLKDpiLmgp6EuLGCovD-QFxrmyNdrbUmKX)

The V2 application-to-controller message protocol is documented in
[V2/MESSAGE_PROTOCOL.md](V2/MESSAGE_PROTOCOL.md). The controller-to-module
protocol is documented in [V2/PROTOCOL.md](V2/PROTOCOL.md).
The production module firmware is in
[V2/Firmware/attiny1624-module](V2/Firmware/attiny1624-module). The ATtiny44A
prototype firmware remains in
[V2/Firmware/attiny44-module](V2/Firmware/attiny44-module).
The selectable 64-position character presets and custom drum settings are
documented in [V2/Code/letters.md](V2/Code/letters.md).
The two incompatible physical V2 builds — the installed 55 mm prototype and
the 50 mm definitive hardware — are explicitly separated in
[V2/variants](V2/variants/README.md).
The parametric mechanical source and fabrication exports are in
[V2/Hardware/mechanical](V2/Hardware/mechanical/README.md).

## What's new
* 120% pure awesomeness.
* Build your own for free or order a kit or ready built module.
* Entirely designed with widely adopted open source software.
* No more gears, direct drive motor
* Assemble in multiple layouts of rows and columns.
* Networked electronics: Connect from one to infinite modules together.
* Custom colors: Request custom colored modules and custom characters.
* Web based interface: Control your modules interactively with your web browser.
* Twitter interface: Create a twitter account for your installation and let the crowd interactively tweet to your modules.

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
