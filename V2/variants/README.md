<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->

# V2 physical designs moved

The former combined variant catalog was removed because it allowed incompatible
parts to appear together. Use exactly one complete folder:

- [`V2/Prototype`](../Prototype/README.md): existing 55 × 43 mm card system,
  50 × 80 mm stickers and 60.3 mm drum.
- [`V2/Final`](../Final/README.md): 50 × 48 mm card system, 45 × 91 mm
  stickers and 55.3 mm drum.

Shared generator code remains under `V2/Hardware`, but it is not a physical
design package. Each version folder owns its profile, contract and generated
manufacturing outputs.
