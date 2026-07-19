"""Unit tests for the pure mode-resolution logic.

These run without a Home Assistant install — see tests/conftest.py.
The positional CHAR_AVAILABLE_MODE interpretation is INFERRED from a single
9430-720 unit; these tests pin the resolver's behavior, not the protocol.
"""

from coleman_mach_ble.const import ALL_MODES, COOL_MODES, HEAT_MODES
from coleman_mach_ble.modes import (
    choose_write_mode,
    modes_from_available,
    resolve_preset_modes,
)

# Ground truth from the live 9430-720 (cool-only): COOL*, FAN*, HEAT supported;
# HEAT ELEC / HEAT GAS not; byte 9 is padding.
UNIT_ARRAY = bytes.fromhex("01010101010101000000")


def test_unit_array_drops_elec_and_gas_keeps_heat():
    result = modes_from_available(UNIT_ARRAY)
    assert "HEAT ELEC" not in result
    assert "HEAT GAS" not in result
    assert "HEAT" in result
    assert result == [
        "COOL HIGH",
        "COOL AUTO HIGH",
        "COOL AUTO LOW",
        "COOL LOW",
        "FAN HIGH",
        "FAN LOW",
        "HEAT",
    ]


def test_none_array_returns_all_modes():
    assert modes_from_available(None) == list(ALL_MODES)


def test_all_zero_array_returns_all_modes():
    assert modes_from_available(bytes(10)) == list(ALL_MODES)


def test_short_array_returns_all_modes():
    assert modes_from_available(bytes.fromhex("010101")) == list(ALL_MODES)


def test_resolve_excludes_heat_on_unit_array():
    result = resolve_preset_modes(UNIT_ARRAY, {"HEAT"})
    assert "HEAT" not in result
    assert result == ["COOL HIGH", "COOL AUTO HIGH", "COOL AUTO LOW", "COOL LOW", "FAN HIGH", "FAN LOW"]


def test_resolve_empty_exclusions_equals_array():
    assert resolve_preset_modes(UNIT_ARRAY, set()) == modes_from_available(UNIT_ARRAY)


def test_resolve_exclude_everything_falls_back_to_base():
    base = modes_from_available(UNIT_ARRAY)
    assert resolve_preset_modes(UNIT_ARRAY, set(base)) == base  # never empty


def test_choose_write_mode_keeps_low_flavor():
    eff = modes_from_available(UNIT_ARRAY)
    assert choose_write_mode(COOL_MODES, eff, "COOL LOW") == "COOL LOW"


def test_choose_write_mode_keeps_auto_flavor():
    eff = modes_from_available(UNIT_ARRAY)
    assert choose_write_mode(COOL_MODES, eff, "COOL AUTO HIGH") == "COOL AUTO HIGH"


def test_choose_write_mode_defaults_to_first_when_no_current():
    eff = modes_from_available(UNIT_ARRAY)
    assert choose_write_mode(COOL_MODES, eff, None) == "COOL HIGH"


def test_choose_write_mode_skips_excluded_preferred():
    eff = resolve_preset_modes(UNIT_ARRAY, {"COOL HIGH"})
    # COOL HIGH excluded, no flavor token in current -> first surviving cool mode
    assert choose_write_mode(COOL_MODES, eff, None) == "COOL AUTO HIGH"


def test_choose_write_mode_returns_none_when_category_empty():
    eff = resolve_preset_modes(UNIT_ARRAY, set(HEAT_MODES))
    assert choose_write_mode(HEAT_MODES, eff, None) is None
