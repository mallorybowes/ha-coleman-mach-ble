
# Coleman Mach BLE — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A Home Assistant custom integration for Coleman Mach Bluetooth RV Air Conditioning units. Provides a `climate` entity with current temperature, set point, and operating mode — all over BLE, no cloud required.  This is vibeware and no guarantees are given.  It works on my AC unit but it's also the only one I can test on.  YMMV.

>**Important notification** - If you are using an HA Yellow system, **\**do not**\** update to HAOS 18+.  There's a kernel level issue that will affect this integration to where it stops working.  The issue has been identified on [this thread](https://github.com/home-assistant/operating-system/issues/4898) but it might take awhile to get the kernel update integrated.  So the "fix" for this is to stay on HAOS 17 until the patch has been released.  AFAIK, this only affects the HA Yellow hardware so if you are using this integration on anything else, you should still be ok.

> **Not affiliated with or endorsed by Airxcel, Inc. or the Coleman Mach brand.**

[In action](https://github.com/user-attachments/assets/5cf54e9b-e62a-4fdb-abf0-b323dec16a7c)

<img width="518" height="274" alt="Screenshot_20260505_123245" src="https://github.com/user-attachments/assets/eb637663-985a-48f3-ac48-c410701fd7a1" />
<img width="637" height="797" alt="Screenshot_20260505_123157" src="https://github.com/user-attachments/assets/1fc85cc8-20fa-4ca4-a05c-9aa590c736e7" />
<img width="641" height="822" alt="Screenshot_20260505_123405" src="https://github.com/user-attachments/assets/093194b6-e6f8-46cd-8c68-645a489fc5b4" />
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

## Compatibility

**The BLE protocol here is reverse-engineered.** There is no published spec — the
characteristic UUIDs and their meanings were derived by observing the Coleman Mach
Smart Comfort app's BLE traffic, and the read order mirrors the app's own
`initReadList`. Nothing here is confirmed by the manufacturer.

Everything below was tested against exactly one unit:

| | Tested configuration |
|---|---|
| AC control board | Coleman Mach / ICM Controls **9430-720 BLE Control Assembly** |
| Unit ID bytes | `2C1A5F` (the device exposes no firmware version over BLE) |
| Reported modes | `01 01 01 01 01 01 01 00 00 00` — 7 supported |
| Host | Home Assistant Yellow, HAOS 17.3, HA 2026.7.4, onboard Bluetooth |

On that unit the supported modes are Cool High / Cool Auto High / Cool Auto Low /
Cool Low / Fan High / Fan Low / Heat. **Heat Elec and Heat Gas are reported as
unsupported and are hidden automatically.** Your unit will likely differ.

### If yours behaves differently

That is expected rather than surprising, and it is useful information — the
capability array is positional and interpreted by inference, and the `UNIT_ID`
field's true semantics and length are unconfirmed across hardware. Differences
have already been found: a second contributor's unit needed fixes to both the
unit ID formatting and the mode filtering.

Please open an issue rather than assuming it is broken. What makes it actionable:

- your AC model / control board part number
- the raw characteristic values, via `logger:` at `debug` for
  `custom_components.coleman_mach_ble` (each read is logged as hex)
- which modes your unit actually offers versus what the integration shows
- for connection problems, the contents of `coleman_mach_ble_failures.log` in your
  config directory, and the `Poll Failures` sensor's attributes

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

The AC requires BLE pairing before it will accept GATT connections. This needs to be done once, or again after the AC is factory reset or power-cycled.

If you see `le-connection-abort-by-local` in the Home Assistant logs, that's the telltale sign — the AC is rejecting the connection because it hasn't been paired (or the bond is stale).

**Re-pairing steps:**

1. From the **Terminal & SSH add-on**, have these commands typed and ready *before* entering pairing mode — the window is short:

   ```
   bluetoothctl
   agent NoInputNoOutput
   default-agent
   pair <YOUR_MAC_ADDRESS> *Don't hit enter on this command until step #2.  The pairing window is short.*
   ```
2. Put the AC into pairing mode (refer to your AC manual).

3. Hit enter for the pairing command above. It will ask for a pairing number — enter the number flashing on the LCD screen on the AC unit.

4. Re-enable the integration if you disabled it during troubleshooting.

> **Note:** The 6-digit code shown in the Coleman Mach Smart Comfort app is an *application-level* PIN, not the same as the BLE pairing code shown on the LCD. Use the LCD code in `bluetoothctl`.

### Stale pairing bond

If the AC was previously paired but is now rejecting connections, remove the old bond first:

```
bluetoothctl remove <YOUR_MAC_ADDRESS>
```

Then follow the re-pairing steps above.

### Pairing fails with AuthenticationCanceled

- **The AC exited pairing mode before the `pair` command ran** — the window is short. Try again: put the AC back in pairing mode and immediately run `pair`.
- **Another device is connected to the AC** — the Coleman Mach app on a phone will hold an exclusive connection. Force-close the app or turn off Bluetooth on the phone, then retry.
- **Power cycle the AC** — if repeated attempts fail, cut power at the breaker for 10 seconds. This clears the AC's pairing state and lets you start fresh.

## License

Apache 2.0 — see [LICENSE](LICENSE).
