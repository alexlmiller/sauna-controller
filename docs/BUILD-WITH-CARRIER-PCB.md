# Build With the Carrier PCB

This is the preferred path for new installs. The Rev B control board carrier
PCB replaces most point-to-point low-voltage module wiring with one organized
board.

## Safety

This project is for **convenience control only**. Use a heater with its own
listed safety systems, keep the manual-reset high-temp protection in series with
the contactor coil, use UL/ETL/listed components where applicable, and have the
high-voltage wiring and final enclosure reviewed and installed by a qualified
electrician. Read [`SAFETY.md`](SAFETY.md) before building.

## What the PCB Includes

- ESP32 DevKitC-32E socket headers
- 24 V input distribution
- 24 V to 5 V conversion for ESP32 and wall panel
- MOSFET outputs for relay coil, RGBW LEDs, and optional AUX output hardware
- Opto inputs for relay feedback and high-temp status
- Resettable PTC branch protection
- DS18B20, door, wall-panel, LED, relay, and high-temp field terminals
- Power/status LEDs and test points

## What You Still Need

- Rev B control board from [`pcb/rev-b/`](../pcb/rev-b/)
- ESP32 DevKitC-32E with ESP32-WROOM-32E or ESP32-WROOM-32D module
- 24 V DIN power supply
- Properly rated heater contactor with 24 VDC coil
- Compatible auxiliary contact block for relay feedback
- Manual-reset high-temp thermostat, such as SUPCO SRL250
- Two DS18B20 temperature probes
- Door reed switch
- 24 V RGBW LED strip, aluminum channel, diffuser, and cable
- Code-compliant enclosure, HV terminal blocks, grounding, and strain relief
- Optional Elecrow CrowPanel 2.1" rotary display for the wall panel

Do not use a WROVER-based DevKitC on the Rev B carrier without changing the PCB
and firmware pin map. Rev B uses GPIO16/GPIO17.

## Board Ordering

Use [`pcb/rev-b/README.md`](../pcb/rev-b/README.md) for KiCad files,
fabrication outputs, BOM/CPL notes, DRC/ERC checklist, and board verification.
That file is the board fabrication and engineering reference; this file is the
installation-oriented build guide.

The rationale behind the board choices is summarized in [`DESIGN.md`](DESIGN.md).

## Field Wiring By Connector

- `24V IN`: external 24 V supply into the board.
- `HIGH TEMP`: sends fused 24 V out to the manual-reset high-temp thermostat and
  receives the return. This loop is in series with the relay coil.
- `RELAY COIL`: connects to the contactor coil.
- `RELAY MONITOR`: connects to the contactor auxiliary contact.
- `LED LIGHTS`: connects to RGBW strip returns plus 24 V LED supply.
- `BENCH TEMP`: bench DS18B20 3-wire connection.
- `CEILING TEMP`: ceiling DS18B20 3-wire connection.
- `DOOR`: reed switch input.
- `CONTROLLER PANEL`: 5 V, GND, TX, RX for the optional wall panel.
- `AUX OUT`: optional protected 24 V low-side output.

`AUX OUT` is exposed as the `AUX Output` switch. The on-board FAULT LED follows
the controller's latched fault state.

## Bring-Up Checklist

1. Inspect polarity, terminal labels, ESP32 orientation, and field wiring before
   applying power.
2. Power the board from 24 V with the heater high-voltage circuit disconnected.
3. Confirm 5 V and 3.3 V rails.
4. Flash [`firmware/control-board/rev-b.yaml`](../firmware/control-board/rev-b.yaml).
5. Confirm both DS18B20 sensors read correctly.
6. Confirm door input changes state.
7. Confirm high-temp and relay feedback inputs with a 24 V bench test.
8. Confirm LED channels one at a time.
9. Confirm contactor coil control with the heater circuit still disconnected.
10. Have the final high-voltage install reviewed and completed by a qualified
    electrician.

## Firmware

```bash
esphome run firmware/control-board/rev-b.yaml
```

Optional wall panel:

```bash
esphome run firmware/wall-panel/wired.yaml
```
