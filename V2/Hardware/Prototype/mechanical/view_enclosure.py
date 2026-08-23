# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""CQ-editor entry point for the capture-fitted printed enclosure."""

from __future__ import annotations

import os
from pathlib import Path

import cadquery as cq

from alphabets_cad.assemblies import captured_enclosure_design_components
from alphabets_cad.parameters import DESIGN, load_design_profile

profile = os.environ.get("ALPHABETS_PROFILE")
parameters = load_design_profile(Path(profile), base=DESIGN) if profile else DESIGN
default_capture = (
    Path(__file__).resolve().parent / "reference/cards-position-capture-final.json"
)
capture_path = Path(os.environ.get("ALPHABETS_CARD_CAPTURE", default_capture))
components = captured_enclosure_design_components(capture_path, parameters)
objects = {component.name: component.shape for component in components}
result = cq.Assembly(name="alphabets-v2-captured-enclosure")
for component in components:
    if component.name == "pawl_definitive":
        continue
    result.add(component.shape, name=component.name, color=component.color)

_show_object = globals().get("show_object")
if callable(_show_object):
    for component in components:
        if component.name == "pawl_definitive":
            continue
        _show_object(
            component.shape,
            name=component.name,
            options={"rgba": component.color.toTuple()},
        )
