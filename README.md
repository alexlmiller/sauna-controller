# AW sauna install — Rev A + M5 Dial

This branch is configured for your **already-built Rev A control box** and an
**M5Stack Dial connected by UART**. Use the two files at the repository root:

- `sauna-controller.yaml` → ESP32 in the control box
- `sauna-panel.yaml` → M5 Dial

The Dial controls heat and lighting directly; Home Assistant is optional.
WiFi is used for firmware updates and optional Home Assistant integration.
The other firmware targets and Rev B build docs are retained for reference;
they are not the installation path for this box.

## Start here: give this README to Claude Code

Ask Claude:

> Set up this Rev A sauna controller and wired M5 Dial using the `aw-install`
> branch and the agent workflow below. Prepare and validate both firmware builds,
> guide me through USB connections, flash both devices, and integrate the control
> box into my Home Assistant. Preserve existing configuration and keep heat OFF.
> Ask me to confirm the physical safety checks before flashing and before any
> supervised heater test. Report what you verified and what still needs a human.

The box is already assembled. The owner handles wiring, USB connections, and
physical checks; Claude handles configuration, builds, flashing, and Home Assistant
setup where its tools allow. If Claude cannot access USB or Home Assistant, it
should give the exact remaining step and resume verification after the owner does it.

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

For initial flashing, power the Dial from the computer's **USB-C (5 V)**.
For permanent power, the box's existing regulated **5 V panel supply can feed
USB-C through a suitable 5 V USB-C power lead/adapter**: `J_PANEL1` pin 3 = +5 V,
pin 4 = GND. Check polarity, cable voltage drop, and available supply capacity.
Disconnect that power feed before plugging into the computer for USB flashing.

**Leave Port B's red wire disconnected.** It is on the Dial's `+5VOUT` rail,
isolated by D8 from the internal supply; it is not the input for powering the
Dial. This follows the [manufacturer schematic, page 2](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/499/Sch_M5Dial.pdf).
The separate rear screw terminal accepts **6–36 V DC**, not the board's 5 V
panel supply. Do not put 24 V on a Grove port or GPIO.
Keep the Dial outside the hot room; its rated operating range is 0–40°C.
[Official Dial pinout and power specifications](https://docs.m5stack.com/en/core/Dial).

## 2. Claude: prepare and validate

1. Inspect the working directory, repository instructions, Git status, available
   ESPHome version, USB access, and existing Home Assistant connection/tools.
   Reuse an existing `aw-install` checkout; preserve local changes and secrets.
   If the repository is not present:

   ```bash
   git clone --branch aw-install --single-branch https://github.com/alexlmiller/sauna-controller.git
   cd sauna-controller
   ```

2. Use ESPHome **2026.10.0**, the version validated here. If unavailable, propose
   a project-local installation and get approval before installing dependencies.
   See [ESPHome installation](https://esphome.io/guides/installing_esphome/).
3. Ask only for missing information: 2.4 GHz WiFi details, Home Assistant URL/access,
   and which device the owner has connected. Have the owner enter secrets locally
   or use an approved secure channel; never print credentials or paste them into
   chat, commits, or logs. Copy `secrets.example.yaml` to `secrets.yaml` **only if
   the latter does not exist**. Generate a unique 32-byte base64 API key and unique
   OTA/fallback AP passwords directly into the ignored secrets file. Do not
   overwrite existing keys. No syslog server is needed.
4. Keep the device names `sauna-controller` and `sauna-panel-wired`: the UART
   provider names depend on them. Use only the two root targets, not the Rev B,
   CrowPanel, or WiFi Dial targets. Keep heat limits and safety logic unchanged.
5. Validate and build both targets before flashing. Treat config output as
   sensitive and do not publish expanded configs. Run from the repository root:

   ```bash
   esphome config sauna-controller.yaml
   esphome config sauna-panel.yaml
   esphome compile sauna-controller.yaml
   esphome compile sauna-panel.yaml
   python3 -m unittest discover -s tests
   ```

The first build downloads toolchain files and fonts and needs internet access.
Do not use sample/fixture credentials in the flashed firmware.

## 3. Claude: flash both devices

After builds pass, confirm the owner has isolated heater mains, checked the
low-voltage wiring, and connected the intended device over USB. Request one
approval for flashing both identified devices; then guide the cable swap without
repeating the approval. Identify the actual serial port rather than guessing.

```bash
# Replace SERIAL_PORT with the verified port for each connected device.
esphome upload sauna-controller.yaml --device SERIAL_PORT
esphome logs sauna-controller.yaml --device SERIAL_PORT

# After the owner connects the Dial:
esphome upload sauna-panel.yaml --device SERIAL_PORT
esphome logs sauna-panel.yaml --device SERIAL_PORT
```

Flash one device at a time. If the Dial does not enter download mode, ask the
owner to disconnect power, hold G0 on its Stamp-S3 module, reconnect USB, then
release G0. Flash **both** targets from this branch: the UART protocol is a
matched pair. Record each device's observed IP and verify boot/WiFi logs without
exposing credentials. Subsequent uploads can use the verified device IP.

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

## 5. Claude: integrate with Home Assistant

Use the owner's existing authorized Home Assistant tools/session. Inspect for an
existing entry first and avoid duplicates. If adding the integration requires
approval in that environment, prepare the exact controller host and request it
once. If no setup-capable tool is available, guide the owner through the UI.
Do not edit Home Assistant's `.storage` files.

- Add the **control box** through **Settings → Devices & services → Add integration
  → ESPHome**, or accept its discovered entry. Use its observed IP/hostname,
  native API port **6053**, and the existing `api_key` from local `secrets.yaml`.
- The **wired Dial does not expose a Home Assistant API** and needs no HA entry.
  No permission for device-initiated HA actions is required.
- Confirm the control-box device is available. Discover its actual entity IDs;
  do not assume IDs from another installation. Verify thermostat, RGBW light,
  bench/ceiling temperatures, door, auxiliary feedback, high-limit, and fault
  entities. Keep thermostat mode OFF throughout setup.
- Compare live temperature/door readings with the Dial and owner observations.
  If approved by the owner, test a lighting change through HA and confirm the
  Dial follows it. Do not start heat, clear a real fault, or create automatic
  heating schedules as an integration test.

[Official ESPHome integration documentation](https://www.home-assistant.io/integrations/esphome/).
The firmware already exposes the entities; no HA YAML package or custom integration
is needed. Use the integration's device page for initial operation.

Finish with a concise handoff: flashed commit/ESPHome version, both observed IPs,
HA device link and discovered entity IDs, checks completed, and unresolved physical
checks. Keep secrets out of the report. The supervised first heat is a separate,
explicit owner action after the installation checks above.

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
| Dial turns off on external power | Check the 5 V USB-C feed under load and polarity; Port B red is not a power input. |

For logs, use `esphome logs sauna-controller.yaml` or `esphome logs sauna-panel.yaml`.

## Wiring reference

[Rev A wiring diagram and pin table](docs/REV-A-WIRING.md) ·
[Rev A KiCad schematic](pcb/rev-a/sauna-controller.kicad_sch) ·
[Safety requirements](docs/SAFETY.md)
