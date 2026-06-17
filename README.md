# Local & Smart Sauna Controller

Open-source sauna convenience control built around ESPHome and Home Assistant. Control your sauna from anywhere with no cloud dependencies or crappy apps and for 1/3rd the cost of the normal commercial units.


The project can be built two ways:

- **Build from components**: hand-wire off-the-shelf modules and DIN parts.
- **Build with the carrier PCB**: use the Rev B control board PCB for cleaner
  wiring and integrated low-voltage distribution.

Both current build paths use the same Rev B firmware and pin map. The optional
wall panel uses an Elecrow CrowPanel 2.1" rotary display over a short wired UART
link, with a WiFi/Home Assistant panel target available for desk testing.

## Safety

This project is for **convenience control only**. It is not a primary safety
system and must not replace the sauna heater's listed safety controls.

- Use only properly rated, UL/ETL/listed components where applicable.
- Use a heater that already has its required high-limit and safety systems.
- Have the enclosure, high-voltage wiring, grounding, overcurrent protection,
  conductor sizing, strain relief, and final installation reviewed and installed
  by a qualified electrician.
- Do not rely on ESPHome, Home Assistant, WiFi, the wall panel, or this PCB as
  life-safety equipment.

Read [`docs/SAFETY.md`](docs/SAFETY.md) before building.

![Controller Box](https://github.com/user-attachments/assets/d93286e9-3aa9-4a17-b4d4-1751c39da36b)

## What It Controls

- Heater contactor with a 24 VDC coil
- Two DS18B20 temperature probes: ceiling and bench
- Door reed switch
- Manual-reset high-temp circuit in series with the contactor coil
- Relay feedback contact for welded/failed relay detection
- 24 V RGBW LED strip through four PWM MOSFET channels
- Optional wall panel over direct 3.3 V UART

## User Interface

The controller exposes its entities through Home Assistant and can also be used
from a phone dashboard or the optional wall panel.

### Home Assistant Device Page

<img width="723" height="761" alt="Home Assistant device page" src="https://github.com/user-attachments/assets/819bb462-3065-4353-bc77-227a327b023d" />

### Phone Dashboard

<img width="606" height="767" alt="Home Assistant phone dashboard" src="https://github.com/user-attachments/assets/f103d0ee-843a-4577-ad8f-8157f9dca8a7" />

## Build Paths

### Option 1: Build From Components

Use an ESP32 DevKitC, MOSFET driver modules, opto input modules, DIN power
supplies, fusing/protection, and terminal blocks. This is best for prototyping
or a one-off hand-wired build.

Start here: [`docs/BUILD-FROM-COMPONENTS.md`](docs/BUILD-FROM-COMPONENTS.md)

### Option 2: Build With the Carrier PCB

Use the Rev B control board carrier PCB. This is the preferred path for new
installs because it reduces point-to-point wiring and integrates the ESP32
carrier, output drivers, opto inputs, PTC protection, 24 V distribution, 5 V
conversion, and field terminals.

Start here: [`docs/BUILD-WITH-CARRIER-PCB.md`](docs/BUILD-WITH-CARRIER-PCB.md)

The design philosophy and current hardware rationale are summarized in
[`docs/DESIGN.md`](docs/DESIGN.md).

## Firmware

Current build targets:

```bash
# Control board
esphome run firmware/control-board/rev-b.yaml

# Normal wired wall panel
esphome run firmware/wall-panel/wired.yaml

# WiFi/Home Assistant wall panel for desk testing
esphome run firmware/wall-panel/wifi.yaml
```

See [`docs/FIRMWARE.md`](docs/FIRMWARE.md) for secrets setup, target layout,
and the legacy Rev A note.

## Wall Panel

The wall panel is optional. The normal installation uses direct 3.3 V UART over
a short Cat5e run and gets 5 V power from the control board. The control board
remains the source of truth for temperature, faults, heat mode, and lighting.

See [`docs/WALL-PANEL.md`](docs/WALL-PANEL.md).

## More Detail

- [`docs/DESIGN.md`](docs/DESIGN.md): design choices and source-of-truth paths.
- [`docs/SAFETY.md`](docs/SAFETY.md): safety boundaries and installation notes.
- [`docs/FIRMWARE.md`](docs/FIRMWARE.md): ESPHome targets and package layout.
- [`docs/WALL-PANEL.md`](docs/WALL-PANEL.md): optional panel behavior and wiring.
- [`pcb/rev-b/README.md`](pcb/rev-b/README.md): KiCad, fabrication, assembly,
  and board verification details.
