"""Parametric mechanical source for the Alphabets V2 module."""

from .assemblies import (
    drum_assembly,
    enclosed_module_assembly,
    enclosure_assembly,
    module_reference_assembly,
)
from .parameters import DESIGN, DesignParameters

__all__ = [
    "DESIGN",
    "DesignParameters",
    "drum_assembly",
    "enclosed_module_assembly",
    "enclosure_assembly",
    "module_reference_assembly",
]
