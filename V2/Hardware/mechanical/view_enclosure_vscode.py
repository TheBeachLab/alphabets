# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""OCP CAD Viewer entry point for the exploded Alphabets V2 enclosure module."""

from __future__ import annotations

import os
from pathlib import Path

from ocp_vscode import reset_show, set_defaults, set_port, show

from alphabets_cad.assemblies import enclosed_module_components
from alphabets_cad.parameters import DESIGN, load_design_profile

profile = os.environ.get("ALPHABETS_PROFILE")
parameters = load_design_profile(Path(profile), base=DESIGN) if profile else DESIGN
components = enclosed_module_components(parameters, exploded=True)
objects = {component.name: component.shape for component in components}

set_port(3939)
reset_show()
set_defaults(axes=True, grid=(True, False, False), ortho=True)
show(
    *(component.shape for component in components),
    names=[component.name for component in components],
    colors=[component.color.toTuple()[:3] for component in components],
    alphas=[component.color.toTuple()[3] for component in components],
)
