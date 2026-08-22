# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Embed the project licence and attribution in Blender documents."""

from pathlib import Path

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = BLENDER_DIR.parents[2]
COPYRIGHT_NOTICE = "Copyright (c) 2014-2026 The Beach Lab (https://beachlab.org)"
SPDX_COPYRIGHT = "2014-2026 The Beach Lab <https://beachlab.org>"
LICENSE_IDENTIFIER = "MIT"
LICENSE_URL = "https://github.com/TheBeachLab/alphabets/blob/master/LICENSE"


def apply_blend_license_metadata(scene: bpy.types.Scene | None = None) -> None:
    """Attach machine-readable metadata and the complete MIT text."""
    scene = scene or bpy.context.scene
    scene["SPDX-FileCopyrightText"] = SPDX_COPYRIGHT
    scene["SPDX-License-Identifier"] = LICENSE_IDENTIFIER
    scene["Copyright"] = COPYRIGHT_NOTICE
    scene["LicenseURL"] = LICENSE_URL

    licence_text = bpy.data.texts.get("LICENSE") or bpy.data.texts.new("LICENSE")
    licence_text.clear()
    licence_text.write((REPOSITORY_ROOT / "LICENSE").read_text())
