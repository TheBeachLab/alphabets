<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->
# Vendored KiCad geometry helpers

- `kicad_round_tracks/` is the Python geometry core from
  [mitxela/kicad-round-tracks 1.6](https://github.com/mitxela/kicad-round-tracks/tree/1.6),
  commit `50374f8f418e57b53683dd18171bb9cf1f9392f8`. The package initializer is
  intentionally headless and does not register the GUI action plugin. The
  vendored action accepts a project-local radius callback and records the
  generated arc-to-corner mapping for adaptive DRC fitting.
- `kicad_teardrops/td.py` is from
  [NilujePerchut/kicad_scripts](https://github.com/NilujePerchut/kicad_scripts/tree/92b5d70be844ad79ed537e0f7c86c5d3d7eb86ee),
  commit `92b5d70be844ad79ed537e0f7c86c5d3d7eb86ee`.

The upstream license for each helper is preserved beside its source.
