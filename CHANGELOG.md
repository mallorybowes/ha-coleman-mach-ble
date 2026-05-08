# Changelog

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
