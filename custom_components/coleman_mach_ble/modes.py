"""Mode-availability resolution for Coleman Mach BLE.

Pure logic, no Home Assistant / bleak imports, so it can be unit-tested in
isolation (see tests/conftest.py).

The positional interpretation of CHAR_AVAILABLE_MODE is INFERRED from a single
9430-720 unit (cool-only, Fahrenheit): byte i == 0x01 => ALL_MODES[i] supported.
It is unconfirmed on other hardware, and that unit's array over-reports HEAT
(reports it available with no furnace installed). This module is therefore
deliberately tolerant: it never returns an empty list and falls back to the full
mode list whenever the data is missing or unusable.
"""

from __future__ import annotations

from .const import ALL_MODES


def modes_from_available(available: bytes | None) -> list[str]:
    """Map the positional AVAILABLE_MODE array to supported mode strings.

    Returns ALL_MODES (order-preserving) when the array is missing, empty, or
    all-zero, so callers never receive an empty list.
    """
    if not available or len(available) < len(ALL_MODES):
        return list(ALL_MODES)
    supported = [
        ALL_MODES[i]
        for i, byte in enumerate(available[: len(ALL_MODES)])
        if byte == 0x01
    ]
    return supported or list(ALL_MODES)


def resolve_preset_modes(available: bytes | None, excluded: set[str]) -> list[str]:
    """Effective preset modes = array-supported minus user-excluded.

    Order follows ALL_MODES. If exclusions would empty the list, the unfiltered
    base is returned instead — never-empty wins over honoring a degenerate
    exclude-everything configuration.
    """
    base = modes_from_available(available)
    effective = [mode for mode in base if mode not in excluded]
    return effective or base


def choose_write_mode(
    category: set[str], effective: list[str], current: str | None
) -> str | None:
    """Pick a concrete write mode within ``category``, constrained to ``effective``.

    Prefers a surviving mode that matches the current fan-speed/auto flavor
    (AUTO/LOW/HIGH token in ``current``); otherwise the first available in-category
    mode (ALL_MODES order). Returns None if the category has no available mode.
    """
    candidates = [mode for mode in effective if mode in category]
    if not candidates:
        return None
    if current:
        if current in candidates:
            return current
        for token in ("AUTO", "LOW", "HIGH"):
            if token in current:
                match = next((c for c in candidates if token in c), None)
                if match:
                    return match
    return candidates[0]
