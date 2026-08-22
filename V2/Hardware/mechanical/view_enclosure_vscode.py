"""OCP CAD Viewer entry point for enclosure design around captured cards."""

from __future__ import annotations

import os
from pathlib import Path

from ocp_vscode import reset_show, set_defaults, set_port, show

from alphabets_cad.assemblies import captured_enclosure_design_components
from alphabets_cad.parameters import DESIGN, load_design_profile

profile = os.environ.get("ALPHABETS_PROFILE")
parameters = load_design_profile(Path(profile), base=DESIGN) if profile else DESIGN
default_capture = (
    Path(__file__).resolve().parent.parent
    / "blender/generated/cards-position-capture.json"
)
capture_path = Path(os.environ.get("ALPHABETS_CARD_CAPTURE", default_capture))
components = captured_enclosure_design_components(capture_path, parameters)
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
