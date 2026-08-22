# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""CQ-editor entry point for the printable rear-open enclosure."""

from __future__ import annotations

import os
from pathlib import Path

from alphabets_cad.assemblies import (
    enclosed_module_assembly,
    enclosed_module_components,
)
from alphabets_cad.parameters import DESIGN, load_design_profile

profile = os.environ.get("ALPHABETS_PROFILE")
parameters = load_design_profile(Path(profile), base=DESIGN) if profile else DESIGN
components = enclosed_module_components(parameters, exploded=True)
objects = {component.name: component.shape for component in components}
result = enclosed_module_assembly(parameters, exploded=True)

_show_object = globals().get("show_object")
if callable(_show_object):
    for component in components:
        _show_object(
            component.shape,
            name=component.name,
            options={"rgba": component.color.toTuple()},
        )
