# Build From Components

This path builds the sauna controller from off-the-shelf modules and DIN parts
instead of the custom carrier PCB. It is useful for prototyping or a one-off
hand-wired build.

New component builds should still use the **Rev B firmware and GPIO map** in
[`firmware/control-board/rev-b.yaml`](../firmware/control-board/rev-b.yaml).
Rev A files are only for early historical boards.

## Safety

This project is for **convenience control only**. Use a heater with its own
listed safety systems, keep the manual-reset high-temp protection in series with
the contactor coil, use UL/ETL/listed components where applicable, and have the
high-voltage wiring and final enclosure reviewed and installed by a qualified
electrician. Read [`SAFETY.md`](SAFETY.md) before building.

## What You Need

Core electronics:

- ESP32 DevKitC-32E with ESP32-WROOM-32E or ESP32-WROOM-32D module
- 24 V DIN power supply
- 24 V to 5 V DC-DC converter for ESP32 and optional wall panel power
- 5 MOSFET driver channels: relay coil, LED R, LED G, LED B, LED W
- 2 opto-isolated 24 V input channels: relay feedback and high-temp status
- 2 DS18B20 temperature probes
- Door reed switch
- Terminal blocks, wire ferrules, DIN rail wiring hardware, and strain relief
- Branch fusing or resettable protection sized for the loads

Sauna/load hardware:

- Properly rated heater contactor with 24 VDC coil
- Compatible auxiliary contact block for relay feedback
- Manual-reset high-temp thermostat, such as SUPCO SRL250
- 24 V RGBW LED strip, aluminum channel, diffuser, and high-temp cable
- Code-compliant enclosure and high-voltage terminal blocks

Optional:

- Elecrow CrowPanel 2.1" rotary display for the wall panel

## Low-Voltage Architecture

- The 24 V DIN supply feeds the contactor coil branch, LED branch, opto wetting
  loops, auxiliary branch if used, and 24 V to 5 V converter.
- The 5 V converter feeds ESP32 `VIN` and, if used, the wall panel.
- All low-voltage returns share a common 0 V reference.
- The contactor coil is switched on the low side by a MOSFET driver.
- RGBW strip channels are switched on the low side by MOSFET drivers.
- Relay feedback and high-temp status are sensed through opto-isolated 24 V
  input modules or equivalent discrete circuits.

## Rev B GPIO Map

Wire the component build to this map so it runs the current firmware. The
authoritative version is the `substitutions:` block in
[`../firmware/control-board/rev-b.yaml`](../firmware/control-board/rev-b.yaml).

| Function | GPIO |
|---|---:|
| Relay coil MOSFET | 23 |
| LED R/G/B/W | 19 / 18 / 17 / 16 |
| Door reed | 25 |
| Bench / ceiling DS18B20 | 26 / 27 |
| Relay feedback | 34 |
| High-temp trip status | 35 |
| Wall panel UART TX / RX | 32 / 33 |
| Fault LED | 22 |
| AUX output | 4 |

GPIO34 and GPIO35 are input-only and do not have internal pull-ups. Your opto
input circuits must provide the required pull-ups or output conditioning.
GPIO22 drives the fault LED, and GPIO4 drives the optional AUX low-side output.

## Wiring Notes

- Put the manual-reset high-temp thermostat in series with the contactor coil
  so it can interrupt heat without software.
- Add flyback suppression across the contactor coil or at the coil driver.
- Fuse/protect the LED branch, coil branch, logic branch, and any auxiliary
  branch based on the actual loads and wire sizes.
- Use shielded/twisted wiring for temperature probes where practical.
- Keep high-voltage wiring away from ESP32, sensor, panel, and low-voltage
  signal wiring.
- Label terminal blocks by function, not just GPIO number.

## Firmware

Flash the control board:

```bash
esphome run firmware/control-board/rev-b.yaml
```

Optional wall panel:

```bash
esphome run firmware/wall-panel/wired.yaml
```

See [`FIRMWARE.md`](FIRMWARE.md) and [`WALL-PANEL.md`](WALL-PANEL.md).
