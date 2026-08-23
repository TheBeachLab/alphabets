<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->

# Shared V2 CadQuery generator

This directory contains shared source code, not a third physical design. The
two fabrication entry points are:

- [`V2/Prototype`](../../Prototype/README.md): 55 mm card, 60.3 mm drum and its
  own captured enclosure;
- [`V2/Final`](../../Final/README.md): 50 mm card, 55.3 mm drum and its own
  captured enclosure.

Each version owns its `design.toml`, variant contract, generated drum, Blender
capture, enclosure and print plate. Do not copy an enclosure or drum between
those folders.

Build one complete matched package from the repository root:

```sh
cd V2/Prototype  # or V2/Final
make setup
make all
make check
```

The generator writes the following inside that version's `generated/` folder:

- `mechanical/cut/*.dxf`: drum and support cutter profiles;
- `mechanical/print/*.stl`: printable reference parts;
- `mechanical/step/*.step`: individual parts and assemblies;
- `mechanical/preview/*.svg`: review projections;
- `mechanical/manifest.json`: exact parameters and bounding boxes;
- `enclosure/`: capture-fitted upper/lower enclosure, selected pawl, STEP files
  and a three-part Bambu A1 Mini print plate.

CadQuery is the manufacturing geometry source. Blender is used to settle the
cards and capture their occupied envelope; the capture is then fed back into
the enclosure exporter. `make check` refuses mixed variant manifests and
verifies that the enclosure cavity is wide enough for the selected cards and
drum.

For a non-fabrication fit experiment, start from one complete profile and apply
[`profiles/fit-check.toml`](profiles/fit-check.toml) as an explicit override.
The generated results remain review artifacts until a real print and drum fit
have been measured.
