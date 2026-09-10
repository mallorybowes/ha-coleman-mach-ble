# Coleman Mach BLE — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Validate](https://github.com/mallorybowes/ha-coleman-mach-ble/actions/workflows/validate.yml/badge.svg)](https://github.com/mallorybowes/ha-coleman-mach-ble/actions/workflows/validate.yml)

Control your Bluetooth Coleman Mach RV air conditioner from Home Assistant. Gives you a
`climate` entity with room temperature, set point, and operating mode — entirely over
BLE. No cloud, no account, no vendor app required.

> **Not affiliated with or endorsed by Airxcel, Inc. or the Coleman Mach brand.**

> **Home Assistant Yellow users:** HAOS **18.0–18.2** broke onboard Bluetooth on the
> Yellow (the BCM4345C0 fails to initialize), which stops this integration working.
> This is **fixed in HAOS 18.3** — *"Bluetooth on Home Assistant Yellow is stable again
> after the regression introduced in 18.0"* — via HW flow control on the Yellow's mini
> UART ([#4957](https://github.com/home-assistant/operating-system/pull/4957)). If you
> are on 18.0–18.2, roll back to 17.3 or wait for 18.3 to leave RC. Background:
> [operating-system#4898](https://github.com/home-assistant/operating-system/issues/4898).
> Other hardware is unaffected.

[▶ See it in action](https://github.com/user-attachments/assets/5cf54e9b-e62a-4fdb-abf0-b323dec16a7c)

<img width="518" height="274" alt="Climate card" src="https://github.com/user-attachments/assets/eb637663-985a-48f3-ac48-c410701fd7a1" />
<img width="637" height="797" alt="Mode selection" src="https://github.com/user-attachments/assets/1fc85cc8-20fa-4ca4-a05c-9aa590c736e7" />
<img width="641" height="822" alt="Device page" src="https://github.com/user-attachments/assets/093194b6-e6f8-46cd-8c68-645a489fc5b4" />

---

## Features

- Room temperature, set point, and operating mode
- Cool (High / Low / Auto High / Auto Low), Fan (High / Low), and Heat modes
- Modes your unit reports as unsupported are hidden automatically
- Celsius and Fahrenheit
- Configurable poll interval
- Rides out the AC's occasional refused BLE connections instead of dropping offline
- Fully local — nothing leaves your network

## Compatibility

**Read this before installing.** The BLE protocol here is **reverse-engineered**. There
is no published spec — the characteristic UUIDs and their meanings were derived by
observing the Coleman Mach Smart Comfort app's Bluetooth traffic, and the read order
mirrors the app's own `initReadList`. None of it is confirmed by the manufacturer.

Everything below was tested against exactly one unit:

| | Tested configuration |
|---|---|
| AC control board | Coleman Mach / ICM Controls **9430-720 BLE Control Assembly** |
| Unit ID bytes | `2C1A5F` — the device exposes no firmware version over BLE |
| Capability array | `01 01 01 01 01 01 01 00 00 00` (7 modes supported) |
| Host | Home Assistant Yellow, HAOS 17.3, HA 2026.7.4, onboard Bluetooth |

On that unit the available modes are Cool High / Cool Auto High / Cool Auto Low / Cool
Low / Fan High / Fan Low / Heat. Heat Elec and Heat Gas are reported as unsupported and
hidden. **Your unit will likely differ**, and that is worth reporting — see
[Contributing](#contributing).

## Requirements

- Home Assistant 2024.1 or newer
- A host with working Bluetooth (onboard, USB, or an ESPHome Bluetooth proxy)
- A Coleman Mach AC with the BLE control module
- The AC **paired** to your host — see [Pairing](#pairing-required-once)

## Installation

### HACS

1. HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/mallorybowes/ha-coleman-mach-ble` as an **Integration**
3. Search for **Coleman Mach BLE**, install, restart Home Assistant

### Manual

Copy `custom_components/coleman_mach_ble/` into your Home Assistant config's
`custom_components/` directory and restart.

## Setup

1. **Settings → Devices & Services → Add Integration**
2. Search for **Coleman Mach BLE**
3. Enter your AC's Bluetooth MAC address — [how to find it](docs/finding_mac_address.md)
4. Give it a name and a poll interval

## Entities

| Entity | Category | What it gives you |
|---|---|---|
| `climate.<name>` | — | Temperature, set point, HVAC mode, and the raw Coleman modes as presets |
| `sensor.<name>_zone` | — | Zone name reported by the unit |
| `sensor.<name>_unit_id` | — | Opaque hex identifier from the control board |
| `sensor.<name>_poll_failures` | Diagnostic | Cumulative BLE poll failures, with `consecutive_failures`, `last_failure`, `last_error` and `capture_log_ok` attributes |

## Options

**Settings → Devices & Services → Coleman Mach BLE → Configure**

| Option | Default | Notes |
|---|---|---|
| Poll interval | 120s | 10–600s. Each poll is a full BLE connect/read/disconnect, so shorter is not free — see below |
| Excluded modes | none | Hide modes your unit reports but does not actually support |

### A note on poll interval

Room temperature moves slowly, and every poll opens and closes a BLE connection against
a module that refuses a small share of them. Measured on the test unit, roughly **2% of
connection attempts fail**, so halving the interval roughly doubles the absolute number
of failures. 120s is a deliberate default. Going below ~60s buys very little and costs
noticeably more failed connections.

Transient failures no longer take the entity offline: a single miss returns the last
known reading, and the entity only goes `unavailable` after two consecutive failures.

## Troubleshooting

### Pairing (required once)

The AC will not accept GATT connections until it has been paired. This is needed once,
and again after a factory reset or a power cycle.

`le-connection-abort-by-local` in the Home Assistant log is the telltale sign — the AC
is refusing the connection because it is unpaired, or the bond has gone stale.

From the **Terminal & SSH** add-on, have these typed and ready **before** you put the AC
into pairing mode — the window is short:

```
bluetoothctl
agent NoInputNoOutput
default-agent
pair <YOUR_MAC_ADDRESS>
```

1. Type everything up to `pair <YOUR_MAC_ADDRESS>` but **do not press Enter yet**
2. Put the AC into pairing mode (see your AC manual)
3. Press Enter on the `pair` command
4. Enter the code flashing on the AC's **LCD screen**
5. Re-enable the integration if you disabled it while troubleshooting

> The 6-digit code in the Coleman Mach Smart Comfort app is an *application* PIN and is
> **not** the BLE pairing code. Use the one on the LCD.

### Stale bond

If the AC was paired before but now refuses connections, remove the old bond and pair
again:

```
bluetoothctl remove <YOUR_MAC_ADDRESS>
```

### Pairing fails with `AuthenticationCanceled`

- **The AC left pairing mode before `pair` ran.** The window is short — retry, with the
  command already typed.
- **Something else is connected.** The Coleman Mach app holds an exclusive connection.
  Force-close it, or turn off Bluetooth on that phone.
- **Power cycle the AC.** Kill the breaker for 10 seconds to clear its pairing state.

### Entity keeps going unavailable

Check `sensor.<name>_poll_failures`. If it is climbing steadily, see Diagnostics below.
Occasional isolated failures are normal and are absorbed automatically; the entity only
drops out after two consecutive misses.

## Diagnostics

Every failed poll is appended to **`coleman_mach_ble_failures.log`** in your Home
Assistant config directory, with the Bluetooth context needed to tell the failure modes
apart:

```
2026-09-10T18:44:47 attempt=1/2 total=34 in_scan=True rssi=-42 advertised=...
  UpdateFailed: Failed to connect after 4 attempt(s): TimeoutError
```

- `in_scan=False` — the AC stopped advertising (powered off, or out of range)
- `in_scan=True` with a healthy `rssi` — the AC is visible but refused the connection

The file rotates at 1 MB. For full protocol-level detail, add to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.coleman_mach_ble: debug
```

Each characteristic read is then logged as hex, which is exactly what is useful in a bug
report.

## Contributing

Different Coleman Mach units **do** behave differently — this is not hypothetical. The
capability array is positional and interpreted by inference, and the `UNIT_ID` field's
true semantics and length are unconfirmed across hardware. The second unit anyone tried
needed fixes to both the unit ID formatting and the mode filtering.

So if yours behaves oddly, that is useful information rather than a nuisance. Please
open an issue including:

- your AC model / control board part number
- the raw characteristic values (enable `debug` logging above — each read is hex)
- which modes your unit actually offers, versus what the integration shows
- for connection problems, `coleman_mach_ble_failures.log` and the `Poll Failures`
  sensor's attributes

Pull requests are welcome. `tests/` covers the pure mode-resolution logic and needs no
Home Assistant install to run:

```
python3 -m pytest tests/
```

## Credits

- [@billchurch](https://github.com/billchurch) — available-mode filtering, and the fix
  for unit ID formatting
- Built and maintained with AI assistance; every change is reviewed, tested against real
  hardware, and validated by `hassfest` and the HACS action before release.

## License

Apache 2.0 — see [LICENSE](LICENSE).
