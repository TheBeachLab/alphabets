"""CQ-editor entry point for the printable rear-open enclosure."""

from alphabets_cad.assemblies import enclosed_module_assembly

result = enclosed_module_assembly(exploded=True)

_show_object = globals().get("show_object")
if callable(_show_object):
    _show_object(result)
