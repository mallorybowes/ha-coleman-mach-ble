# Finding Your Coleman Mach AC's Bluetooth MAC Address

The easiest way to find the MAC address is using the **nRF Connect** app by Nordic Semiconductor.

> **iOS limitation:** Apple does not expose real Bluetooth MAC addresses on iOS for privacy reasons. If you only have an iPhone/iPad, see the [iOS alternatives](#ios-alternatives) section below.

---

## Android — nRF Connect

1. Install **nRF Connect for Mobile** from the Google Play Store.

2. Open the app and tap the **Scanner** tab at the bottom.

3. Tap **SCAN** (top right). You will see a list of nearby Bluetooth devices start to appear.

4. Power on your Coleman Mach AC if it isn't already.

5. Look for a device named **"Thermostat"** in the list. It may also appear as an unnamed device.
   - If you're unsure which device is the AC, stand close to it and note which device has a strong RSSI signal (a value closer to 0 dBm, e.g. −40 dBm is stronger than −80 dBm).
   - You can also filter by tapping the **filter icon** and searching for the Coleman Mach service UUID: `c9282723-4680-491b-a904-c066fa81061f`

6. The **MAC address** is displayed in small text directly below the device name, in the format `XX:XX:XX:XX:XX:XX`.

7. Tap the device row to see more details and confirm it's the right device — you should see the service UUID `c9282723-4680-491b-a904-c066fa81061f` listed under **Advertised Services** or after tapping **Connect → Services**.

8. Note the MAC address — you'll enter it during the Home Assistant integration setup.

---

## iOS Alternatives

Since iOS hides real MAC addresses, use one of these methods instead:

### Option A — Check your router's device list
1. Log in to your router/Wi-Fi access point admin page.
2. Look for a Bluetooth section, or check the ARP/DHCP table.
   - Note: Bluetooth devices don't connect to Wi-Fi, so this only works if your router also has Bluetooth scanning (e.g. some Eero, UniFi, or GL.iNet routers).

### Option B — Use bluetoothctl on the Home Assistant host
From the **Terminal & SSH add-on** in Home Assistant:

```bash
bluetoothctl
scan on
```

Wait 10–15 seconds while nearby devices are discovered. Look for a device named **"Thermostat"** or any unknown device that appears when your AC is powered on (and disappears when it's off). The MAC address is shown next to the device name:

```
[NEW] Device 00:A0:50:XX:XX:XX Thermostat
```

Press `Ctrl+C` or type `scan off` then `quit` when done.

### Option C — Borrow an Android device
Use any Android phone or tablet to run nRF Connect as described above.

---

## Tips

- The AC must be powered on and not already connected to another device (e.g. the Coleman Mach app) for it to appear in a scan.
- If the device doesn't appear, try power cycling the AC.
- The MAC address won't change between power cycles — once you have it, you only need to find it once.
