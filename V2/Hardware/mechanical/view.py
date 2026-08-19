"""CQ-editor entry point for the Alphabets V2 reference module."""

from alphabets_cad.assemblies import module_reference_assembly

result = module_reference_assembly()

# CQ-editor injects show_object when it executes this file. Keeping the guard
# also makes the entry point importable by the command-line test suite.
_show_object = globals().get("show_object")
if callable(_show_object):
    _show_object(result)
