# AW sauna install — Rev A + M5 Dial

For the assembled Rev A box, with a wired M5 Dial and Home Assistant.
The Dial works independently of Home Assistant; WiFi provides updates and HA access.

Give this README to Claude Code:

> Follow this guide to configure and flash both devices, then add the control box
> to my Home Assistant. Preserve existing settings and secrets. Keep heat OFF;
> guide me through the physical checks and report anything you cannot verify.

## 1. Connect the Dial

Isolate heater mains before wiring or flashing. Keep the heater's listed protections
and manual-reset high-limit intact. See [safety requirements](docs/SAFETY.md).

**Power:** run a separately fused feed from the box's **24 VDC supply distribution**
to the Dial's **rear power terminal**, matching its +/− markings. Use supply ground
for −, shared with the control board. Do not use the switched contactor-coil feed.
The rear terminal accepts 6–36 VDC. Keep the Dial outside the hot room (0–40°C rating).
[Dial specifications](https://docs.m5stack.com/en/core/Dial).

**UART:** use Port B (black connector), 3.3 V signals at 115200 baud:

| Rev A `J_PANEL1` | Dial Port B |
|---|---|
| Pin 1: TX / GPIO14 | White / GPIO1 RX |
| Pin 2: RX / GPIO4 | Yellow / GPIO2 TX |
| Pin 4: GND | Black / GND |
| Pin 3: +5 V | Leave disconnected |

Leave Port B's **red wire disconnected**. Never put 24 V on a Grove port or GPIO.
[Rev A wiring diagram and connector pins](docs/REV-A-WIRING.md).

## 2. Claude: prepare firmware

Reuse an existing `aw-install` checkout and preserve local changes. Otherwise:

```bash
git clone --branch aw-install --single-branch https://github.com/alexlmiller/sauna-controller.git
cd sauna-controller
```

- Use **ESPHome 2026.10.0**. Ask before installing missing dependencies;
  prefer a project-local environment. [ESPHome installation](https://esphome.io/guides/installing_esphome/).
- Ask for missing WiFi details, HA access, and the connected USB device.
- Create `secrets.yaml` from `secrets.example.yaml` only if absent. Have the owner
  enter WiFi credentials securely; generate unique OTA/AP passwords and a 32-byte
  base64 API key. Preserve existing keys. Never publish secrets or expanded configs.
- Use only the root targets below. Keep device names `sauna-controller` and
  `sauna-panel-wired`; UART routing depends on them. Keep safety settings intact.

```bash
esphome config sauna-controller.yaml
esphome config sauna-panel.yaml
esphome compile sauna-controller.yaml
esphome compile sauna-panel.yaml
python3 -m unittest discover -s tests
```

First builds need internet access. Do not flash placeholder credentials.

## 3. Claude: flash both devices

After builds pass, confirm heater mains are isolated and wiring is checked.
Obtain approval to flash both devices, then connect **one at a time** over USB.
Identify each serial port; replace `SERIAL_PORT` below. Use computer USB-C to power
and flash the Dial with its external 24 V feed disconnected.

```bash
# Control-box ESP32
esphome upload sauna-controller.yaml --device SERIAL_PORT
esphome logs sauna-controller.yaml --device SERIAL_PORT

# M5 Dial, after swapping the USB cable
esphome upload sauna-panel.yaml --device SERIAL_PORT
esphome logs sauna-panel.yaml --device SERIAL_PORT
```

If the Dial will not flash: disconnect power, hold G0 on its Stamp-S3 module,
connect USB, then release G0. Flash both targets; they use a matched UART protocol.
Verify boot/WiFi logs and record both IPs. Later uploads can use the device IP.

## 4. Check before enabling heater power

With heater mains still isolated, reconnect normal low-voltage power:

- Heat boots **OFF**; the Dial shows temperatures without `NO LINK`.
- Bench/ceiling readings match the probes; door status follows the reed switch.
- Verify auxiliary feedback and high-limit status against the physical circuit.
  The high-limit must physically interrupt coil power.
- Check lights, brightness, and all four presets.
- Confirm OFF and power cycling leave the contactor de-energized. Have the
  installer verify the heater safety circuit before a supervised first heat.

Allow **four minutes** for the thermostat's startup/minimum-off delay. Correct a
fault's cause before clearing it: close the door, restore valid ceiling readings
and the high-limit loop, and verify the contactor is off. Clearing does not restart
heat. `NO LINK` does
not stop an active heating session—use the physical disconnect when needed.

## 5. Claude: add Home Assistant

Use authorized HA tools or guide the owner through the UI. Reuse an existing
integration entry; do not edit `.storage` files.

1. Add **ESPHome** under **Settings → Devices & services**, or accept discovery.
   Use the control box's IP, port **6053**, and `api_key` from `secrets.yaml`.
2. Add only the control box. The wired Dial needs no HA entry or action permissions.
3. Discover actual entity IDs. Verify thermostat, RGBW light, temperatures, door,
   auxiliary feedback, high-limit, and fault status. Keep heat OFF.
4. Compare HA readings with the Dial. Test lighting with the owner's agreement.
   Do not start heat, clear real faults, or create heating schedules during setup.

[HA integration reference](https://www.home-assistant.io/integrations/esphome/).
If tools cannot access USB or HA, give the owner the exact step, then verify the
result. Finish with firmware version/commit, IPs, HA device link, entity IDs, and
remaining physical checks. Keep credentials out of the handoff.

## Dial controls

| Action | Result |
|---|---|
| Single ring press or background tap | Next page: temperature → lights → status |
| Turn on temperature page | Adjust target, 150–200°F; does not start heat |
| Double ring press on temperature page | Heat ON/OFF |
| Turn on lights page | Adjust brightness |
| Double ring press on lights page | Lights ON/OFF |
| Tap a color button | Select preset |
| Double ring press on status page | Request fault clearing |

For `NO LINK`, check common ground, crossed TX/RX, Port B, and both firmware versions.
For IDLE, check target temperature and the four-minute delay. For power trouble,
check the rear terminal's polarity and 24 V feed under load.
