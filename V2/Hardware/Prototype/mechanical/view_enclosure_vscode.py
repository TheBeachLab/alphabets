# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""OCP CAD Viewer entry point for enclosure design around captured cards."""

from __future__ import annotations

import os
from pathlib import Path

import cadquery as cq
from ocp_vscode import Render, reset_show, set_defaults, set_port, show

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


def _viewer_group(name: str, members: tuple) -> cq.Assembly:
    group = cq.Assembly(name=name)
    for component in members:
        group.add(component.shape, name=component.name, color=component.color)
    return group


group_members = {
    "enclosure": tuple(
        component
        for component in components
        if component.name == "enclosure" or component.name.startswith("enclosure_")
    ),
    "pua_definitiva": tuple(
        component for component in components if component.name == "pawl_definitive"
    ),
    "pua_prototipo": tuple(
        component for component in components if component.name == "pawl_prototype"
    ),
    "tambor": tuple(
        component
        for component in components
        if component.name
        in ("motor_side", "shaft_side", "support_front", "support_back")
    ),
    "cards": tuple(
        component for component in components if component.name.startswith("card_")
    ),
    "stickers": tuple(
        component for component in components if component.name.startswith("sticker_")
    ),
    "motor": tuple(
        component for component in components if component.name.startswith("motor_")
    ),
    "electronics": tuple(
        component
        for component in components
        if component.name == "electronics_card_envelope"
    ),
    "envelopes": tuple(
        component for component in components if component.name.startswith("capture_")
    ),
}
groups = {}
group_colors = {}
group_alphas = {}
for name, members in group_members.items():
    if not members:
        continue
    if name == "enclosure" or name.startswith("pua_"):
        groups[name] = members[0].shape
        group_colors[name] = members[0].color.toTuple()[:3]
        group_alphas[name] = members[0].color.toTuple()[3]
    else:
        groups[name] = _viewer_group(name, members)
        group_colors[name] = None
        group_alphas[name] = None
group_modes = {
    name: Render.NONE if name == "pua_definitiva" else Render.ALL for name in groups
}

set_port(3939)
reset_show()
set_defaults(axes=True, grid=(True, False, False), ortho=True)
show(
    *groups.values(),
    names=list(groups),
    colors=list(group_colors.values()),
    alphas=list(group_alphas.values()),
    modes=list(group_modes.values()),
)
