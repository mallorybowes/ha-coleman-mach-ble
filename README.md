# Coleman Mach BLE — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A Home Assistant custom integration for Coleman Mach Bluetooth AC units. Provides a `climate` entity with current temperature, set point, and operating mode — all over BLE, no cloud required.

> **Not affiliated with or endorsed by Airxcel, Inc. or the Coleman Mach brand.**

[Screencast_20260505_013413_2.webm](https://github.com/user-attachments/assets/5cf54e9b-e62a-4fdb-abf0-b323dec16a7c)

---

## Features

- Current room temperature
- Set point control
- Operating mode (Cool High/Low, Fan, Heat, etc.)
- Celsius/Fahrenheit support
- Configurable poll interval
- Works entirely local over Bluetooth — no cloud, no app required

## Requirements

- Home Assistant 2024.1 or newer
- A Raspberry Pi (or other host) with Bluetooth support
- Coleman Mach AC unit with BLE module

## Installation

### HACS (recommended)

1. In HACS, go to **Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/mallorybowes/ha-coleman-mach-ble` as an **Integration**
3. Search for "Coleman Mach BLE" and install
4. Restart Home Assistant

### Manual

Copy the `custom_components/coleman_mach_ble/` folder into your HA config's `custom_components/` directory, then restart Home Assistant.

## Setup

1. Go to **Settings → Integrations → Add Integration**
2. Search for "Coleman Mach BLE"
3. Enter the Bluetooth MAC address of your AC unit (find it with a BLE scanner app or your router's device list.  [How-to](docs/finding_mac_address.md) located in the /docs directory.)
4. Set a name and poll interval

## Troubleshooting

### AC shows as unavailable / cannot connect

The AC requires BLE "Just Works" pairing before it will accept GATT connections. This needs to be done once, or again after the AC is factory reset or power-cycled.

**Re-pairing steps:**

1. From the **Terminal & SSH add-on**, have these commands typed and ready *before* entering pairing mode — the window is short:

   ```
   bluetoothctl
   agent NoInputNoOutput
   default-agent
   pair <YOUR_MAC_ADDRESS> *Don't hit enter on this command until step #2.  The pairing window is short.*
   ```
2. Put the AC into pairing mode (refer to your AC manual).

   `NoInputNoOutput` forces "Just Works" pairing with no PIN required at the BLE level.

3.  Hit enter for the pairing command above.  It will ask for a pairing number which will be the number flashing on the LCD screen on the AC unit.

4. Re-enable the integration if you disabled it during troubleshooting.

> **Note:** The 6-digit code shown in the Coleman Mach Smart Comfort app is an *application-level* PIN, not a BLE pairing passkey. Do not enter it in `bluetoothctl`.

### Stale pairing bond

If the AC was previously paired but is now rejecting connections, remove the old bond first:

```
bluetoothctl remove <YOUR_MAC_ADDRESS>
```

Then follow the re-pairing steps above.

## License

Apache 2.0 — see [LICENSE](LICENSE).
