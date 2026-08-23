# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""CQ-editor entry point for the Alphabets V2 reference module."""

from __future__ import annotations

import os
from pathlib import Path

from alphabets_cad.assemblies import (
    module_reference_assembly,
    module_reference_components,
)
from alphabets_cad.parameters import DESIGN, load_design_profile

# Select a complete profile with ALPHABETS_PROFILE. Blank keeps the shared
# dataclass defaults; the fabrication entry points live in V2/Prototype and
# V2/Final and always supply their own design.toml.
profile = os.environ.get("ALPHABETS_PROFILE")
parameters = load_design_profile(Path(profile), base=DESIGN) if profile else DESIGN
components = module_reference_components(parameters)
objects = {component.name: component.shape for component in components}
result = module_reference_assembly(parameters)

# CQ-editor gets every part as its own selectable/visible object. `result` is
# retained as the colored fabrication assembly for STEP export and automation.
_show_object = globals().get("show_object")
if callable(_show_object):
    for component in components:
        _show_object(
            component.shape,
            name=component.name,
            options={"rgba": component.color.toTuple()},
        )
