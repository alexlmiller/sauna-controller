# Design Notes

This file captures the durable design rationale for the current sauna
controller. It intentionally avoids copying large YAML or KiCad details; the
live source files listed below are authoritative.

## Source Of Truth

- Control board firmware: [`../firmware/control-board/rev-b.yaml`](../firmware/control-board/rev-b.yaml)
- Shared control logic: [`../firmware/control-board/packages/common.yaml`](../firmware/control-board/packages/common.yaml)
- Wall panel firmware: [`../firmware/wall-panel/`](../firmware/wall-panel/)
- Rev B board design: [`../pcb/rev-b/`](../pcb/rev-b/)
- Rev B board database: [`../pcb/rev-b/tools/design.py`](../pcb/rev-b/tools/design.py)

## Safety Boundary

The project is for convenience control only. The heater must have its own
listed safety systems, and the manual-reset high-temp loop stays in series with
the contactor coil so it can interrupt heat without software.

The control board should fail with heat off if the ESP32 reboots, firmware
crashes, WiFi drops, Home Assistant is unavailable, or the wall panel is
unplugged. That fail-off behavior is useful, but it is not a substitute for a
listed safety system or code-compliant installation.

## Hardware Philosophy

- Keep high-voltage switching outside the PCB. The board controls a 24 VDC
  contactor coil; the contactor handles heater power.
- Use a 24 V low-voltage cabinet bus for field wiring, contactor coil, opto
  wetting loops, LED strip power, and auxiliary loads.
- Generate 5 V on the carrier board for the ESP32 DevKitC and optional wall
  panel.
- Keep the ESP32 as a socketed DevKitC module instead of placing the ESP32
  module directly on the carrier board. This avoids RF layout, USB, boot strap,
  and assembly complexity.
- Use the Espressif ESP32-DevKitC V4 with an ESP32-WROOM-32E or WROOM-32D
  module. Do not use WROVER DevKitC variants on Rev B because GPIO16/GPIO17 are
  used by the board.
- Prefer grouped, field-serviceable connectors over minimum board area. The
  connector placement follows the physical cabinet: 24 V supply at the top,
  sauna-room wiring along the bottom, LEDs on the left, and contactor wiring on
  the right.
- Use resettable PTC protection on the low-voltage board branches instead of
  external DIN fuse holders.

## Control Model

The control board owns the heater, faults, sensors, and outputs. Home Assistant
and the wall panel request state changes; they are not required for the board to
run its local control logic.

The wall panel is a client. On boot it syncs from the control board before
publishing user changes, so it does not overwrite Home Assistant or control
board state with stale defaults.

## Current GPIO Map

The authoritative map is the `substitutions:` block in
[`../firmware/control-board/rev-b.yaml`](../firmware/control-board/rev-b.yaml).
For a hand-wired build, wire to that file rather than an older Rev A pin list.

Rev B uses:

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

GPIO34 and GPIO35 are input-only and do not have internal pull-ups. The Rev B
carrier provides the required input conditioning; a hand-wired component build
must do the same.
