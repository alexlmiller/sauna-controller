# AW sauna install — Rev A + M5 Dial

This branch is configured for your **already-built Rev A control box** and an
**M5Stack Dial connected by UART**. Use the two files at the repository root:

- `sauna-controller.yaml` → ESP32 in the control box
- `sauna-panel.yaml` → M5 Dial

The Dial controls heat and lighting directly; Home Assistant is optional.
WiFi is used for firmware updates and optional Home Assistant integration.
The other firmware targets and Rev B build docs are retained for reference;
they are not the installation path for this box.

## 1. Connect the Dial

Keep heater mains isolated while checking wiring and flashing. This is convenience
control: the heater's listed protections and the physical manual-reset high-limit
must remain in place. See [safety requirements](docs/SAFETY.md).

Use the Dial's **Port B** (black connector) for 3.3 V UART at 115200 baud:

| Rev A control board | M5 Dial Port B |
|---|---|
| J_PANEL1 pin 1: TX / GPIO14 | White / GPIO1 (RX) |
| J_PANEL1 pin 2: RX / GPIO4 | Yellow / GPIO2 (TX) |
| J_PANEL1 pin 4: GND | Black / GND |

TX and RX cross. This is a short direct UART cable, not Ethernet or RS-485.
The Rev A board uses the four-position `J_PANEL1` screw terminal.
Verify connector pin numbering against the [Rev A wiring reference](docs/REV-A-WIRING.md).

For initial setup, power the Dial over **USB-C (5 V)** and leave Port B's red
wire disconnected. For permanent power, its **rear screw terminal accepts
6–36 V DC**: a suitably fused 24 V supply from the box can feed that terminal,
with correct polarity and a shared ground. Do not put 24 V on a Grove port or
GPIO, or connect the board's 5 V panel output to the rear terminal.
Keep the Dial outside the hot room; its rated operating range is 0–40°C.
[Official Dial pinout and power specifications](https://docs.m5stack.com/en/core/Dial).

## 2. Get the firmware and enter WiFi details

Use ESPHome **2026.10.0** (the version used to validate this branch).
If needed, follow [ESPHome's installation instructions](https://esphome.io/guides/installing_esphome/).

```bash
git clone --branch aw-install --single-branch https://github.com/alexlmiller/sauna-controller.git
cd sauna-controller
cp secrets.example.yaml secrets.yaml
openssl rand -base64 32
```

Edit `secrets.yaml`: enter your 2.4 GHz WiFi name/password, choose unique fallback
AP and OTA passwords, and paste the generated key into `api_key`. Keep this file
private; Git ignores it. No logging server or Home Assistant entity IDs are needed.

## 3. Flash both devices over USB

Flash one device at a time so the serial-port choice is unambiguous. Run these
commands from the repository root. The first build downloads toolchain files and
fonts and needs internet access.

```bash
# ESP32 in the control box
esphome run sauna-controller.yaml

# M5 Dial
esphome run sauna-panel.yaml
```

Select the connected USB serial port for the first flash. If the Dial does not
enter download mode, disconnect power, hold G0 on its Stamp-S3 module, reconnect
USB, then release G0. Subsequent updates can use WiFi through the same commands.
Flash **both** targets from this branch: the wired command protocol is a matched pair.

## 4. Check the installation before enabling heater power

With heater mains still isolated, power the low-voltage box and Dial:

1. Both boot with heat **OFF**. The Dial should show real temperatures and clear
   its `NO LINK` warning once UART data arrives.
2. Check bench and ceiling temperatures are plausible and correctly assigned.
   Each probe has its own bus; no sensor address needs to be entered.
3. On the status page, open/close the door and check the displayed state follows it.
   Verify the contactor auxiliary feedback and high-limit indication against the
   physical circuit. An open high-limit must physically interrupt coil power.
4. Test the lights, brightness, and presets. Check R/G/B/W against the reference
   if the colors do not match.
5. Verify heat OFF and power cycling leave the contactor de-energized. Have the
   installer verify the contactor, manual-reset high-limit, and heater safety
   circuit before restoring heater power for a supervised first heat.

The thermostat has a **four-minute startup/minimum-off delay**, so requesting heat
may show IDLE before the contactor energizes. Faults force heat OFF; clearing a
fault does not restart heating. Investigate the cause before clearing it.

## Using the Dial

- **Single press** of the ring, or single tap on the page background: next page
  (temperature → lights → status).
- **Turn** on the temperature page: adjust target, 150–200°F. Turning alone does
  not turn heat on.
- **Double press/tap** on the temperature page: toggle heat ON/OFF.
- **Turn** on the lights page: brightness; **double press/tap**: lights ON/OFF.
  Tap a preset button to choose its color.
- **Double press/tap** on the status page: request fault clearing, after the cause
  has been corrected.

The control box remains authoritative. A lost UART connection displays `NO LINK`;
it is **not an emergency stop** and does not itself turn off an active session.
Use the heater's physical disconnect when needed.

## Troubleshooting

| Symptom | Check |
|---|---|
| `NO LINK` or blank temperatures | Common ground, crossed TX/RX, correct Port B wires, both root firmware files flashed. |
| Heat stays OFF / fault shown | Read status, check door/high-limit/aux feedback; correct the cause first. |
| Heat says IDLE | Allow the four-minute minimum-off/startup delay; check target is above current temperature. |
| One temperature missing | Probe power/data/GND and the correct dedicated bus. |
| Dial turns off on external power | Rear terminal polarity and 6–36 V supply; use USB to isolate power issues. |

For logs, use `esphome logs sauna-controller.yaml` or `esphome logs sauna-panel.yaml`.
Optional Home Assistant setup: add the control box through the ESPHome integration
using the API key in `secrets.yaml`; the Dial does not need Home Assistant.

## Wiring reference

[Rev A wiring diagram and pin table](docs/REV-A-WIRING.md) ·
[Rev A KiCad schematic](pcb/rev-a/sauna-controller.kicad_sch) ·
[Safety requirements](docs/SAFETY.md)
