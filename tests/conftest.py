"""Load the pure coleman_mach_ble.modes / .const modules in isolation.

The integration package's __init__.py imports homeassistant, so importing
custom_components.coleman_mach_ble.modes normally needs the full HA stack.
modes.py and const.py have no HA dependencies, so register a stub package and
load just those two submodules by file path. This lets `from .const import ...`
resolve without executing __init__.py — so `python3 -m pytest` works with zero
Home Assistant install.
"""

import importlib.util
import pathlib
import sys
import types

_PKG = "coleman_mach_ble"
_PKG_DIR = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components"
    / "coleman_mach_ble"
)

if _PKG not in sys.modules:
    _stub = types.ModuleType(_PKG)
    _stub.__path__ = [str(_PKG_DIR)]
    sys.modules[_PKG] = _stub


def _load(name: str):
    full = f"{_PKG}.{name}"
    if full in sys.modules:
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(full, _PKG_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    return mod


_load("const")  # must load before modes (modes does `from .const import ...`)
_load("modes")
