# Changelog

## [Unreleased]

### Changed
- Troubleshooting: document that an ESPHome Bluetooth proxy cannot drive this AC, because the pairing bond lives in BlueZ on the Home Assistant host and cannot be transferred to an ESP32

## [v1.23.0] - 2026-09-10

### Added
- hassfest and HACS validation workflows, run on push, PR, and weekly

### Fixed
- LICENSE was a truncated Apache-2.0 (163 of 201 lines), so GitHub reported SPDX `NOASSERTION` and HACS validation failed. Replaced with the canonical text
- Brand assets moved to `custom_components/coleman_mach_ble/brand/` — HACS looks for `brand/`, not `brands/`
- Removed the `homeassistant` key from `manifest.json`, which is not valid for custom integrations; the minimum Home Assistant version now lives in `hacs.json`
- Manifest keys sorted as hassfest requires (`domain`, `name`, then alphabetical)

### Changed
- README rewritten: documents the tested control board and that the protocol is reverse-engineered, plus entities, options, diagnostics and contributing guidance
- Corrected the Home Assistant Yellow notice — HAOS 18.0-18.2 break onboard Bluetooth, but this is fixed in 18.3

## [v1.22.0] - 2026-09-10

### Added
- `Poll Failures` diagnostic sensor (`total_increasing`) exposing the cumulative BLE poll failure count, with `consecutive_failures`, `last_failure`, `last_error` and `capture_log_ok` attributes. It overrides `available` to stay reporting while the coordinator is failing, which is exactly when it is needed
- Failure capture to `coleman_mach_ble_failures.log` in the config dir, recording BLE context (`in_scan`, `rssi`, last advertisement time) plus the exception. Full traceback is written only for the first failure of a streak; the file rotates at 1 MB for a ~2 MB ceiling
- Options flow for `poll_interval`, so it can be changed from the UI without re-adding the integration. An update listener reloads the entry so the change takes effect immediately

### Changed
- Tolerate transient BLE failures instead of going `unavailable` on the first miss. `MAX_CONSECUTIVE_FAILURES = 2` returns the last known data for a single blip; a real outage still surfaces after ~4 minutes
- Default poll interval 30s -> 120s

### Notes
Measured over 16.1h on the 30s interval: 34 failures (~2.1/hr, ~2% of connect attempts), every one an isolated single, never back to back — so a threshold of 2 absorbs all of them. Each failure was `in_scan=True` with rssi -39..-57 and `Failed to connect after 4 attempt(s): TimeoutError`, i.e. the AC advertising normally but refusing the GATT connection. Not range, and not contention on the HA side: the host is on ethernet with `wlan0` down (ruling out WiFi/BT coexistence on the combo bcm43438), and BLE failures showed no correlation with Music Assistant playback (5.9% observed vs 6.1% expected by chance). The 120s interval cuts connect attempts ~72%, which should take failures from ~50/day to ~14/day.

## [v1.21] - 2026-05-08

### Fixed
- OFF mode now correctly writes `OFF` to the device (previously wrote `FAN LOW`, causing the unit to stay on)
- Brief "unavailable" flash when changing modes — BLE write and coordinator poll were racing for the same connection; serialized with a lock

### Changed
- Troubleshooting docs updated: added `le-connection-abort-by-local` as the log indicator for missing pairing, and a new `AuthenticationCanceled` section covering common causes and fixes

## [v1.2] - 2026-05-08

### Fixed
- OFF mode selection in the dropdown now attempts to turn the unit off

## [v1.1] - 2026-05-05

### Added
- Brands directory with icon for HACS

## [v1.0] - 2026-05-05

- Initial release
