"""Parametric mechanical source for the Alphabets V2 module."""

from .assemblies import (
    drum_assembly,
    drum_components,
    drum_stop_rotation_degrees,
    enclosed_module_assembly,
    enclosed_module_components,
    enclosure_assembly,
    enclosure_components,
    module_reference_assembly,
    module_reference_components,
    mounted_card_components,
)
from .parameters import DESIGN, DesignParameters, load_design_profile
from .parts import (
    captured_drum_enclosure_parts,
    captured_enclosure_limits,
    captured_pawl_parts,
)

__all__ = [
    "DESIGN",
    "DesignParameters",
    "captured_drum_enclosure_parts",
    "captured_enclosure_limits",
    "captured_pawl_parts",
    "drum_assembly",
    "drum_components",
    "drum_stop_rotation_degrees",
    "enclosed_module_assembly",
    "enclosed_module_components",
    "enclosure_assembly",
    "enclosure_components",
    "load_design_profile",
    "module_reference_assembly",
    "module_reference_components",
    "mounted_card_components",
]
