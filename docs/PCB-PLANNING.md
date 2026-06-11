# Sauna Controller PCB Planning

This document captures the intended scope for a first custom low-voltage PCB.
The existing controller is already functional; this board is an upgrade to
clean up wiring and replace the loose ESP32, MOSFET breakout boards, opto
modules, DIN-rail low-voltage fuses, DC-DC converter, and low-voltage
distribution.

> **Post-install note:** The first custom PCB has been ordered, assembled, and
> brought up. Core functions work. Lessons learned and candidate changes for
> the next board spin are tracked in
> [`PCB-REV-B-NOTES.md`](PCB-REV-B-NOTES.md).

## Scope

### In Scope

- Carrier board for the existing ESP32 DevKitC v4 dev board.
- 24 VDC input from the existing DIN power supply.
- On-board 24 V to 5 V conversion.
- On-board low-voltage fusing/protection so separate DIN fuse holders are no
  longer required.
- 5 V distribution for:
  - ESP32 dev board VIN.
  - Door/panel connector power.
- 24 V distribution for:
  - Contactor coil safety/control loop.
  - RGBW LED strip common positive.
  - 24 V field sensing/reference where needed.
- Low-side MOSFET outputs for:
  - Contactor coil.
  - RGBW LED channels.
- Protected GPIO inputs for:
  - Door reed switch.
  - Contactor auxiliary feedback.
  - High-limit feedback.
- DS18B20 probe connectors for:
  - Bench temperature.
  - Ceiling temperature.
- Panel wiring connector:
  - 5 V.
  - GND.
  - Direct UART TX/RX signal pins.
- Terminal blocks and labeling to make field wiring obvious.

### Out of Scope

- 240 VAC heater current path.
- Contactor power poles.
- Main service disconnect, breaker, GFCI, or high-voltage protection.
- Replacement for the manual-reset high-limit safety.
- CrowPanel electronics. The board only needs a clean connector for its cable.
- Separate DIN fuse holders for the low-voltage branches.

The high-voltage heater path and code-required wiring remain separate DIN/enclosure
wiring and should be reviewed/installed by a qualified electrician.

Target enclosure contents after this upgrade:

- Custom low-voltage controller PCB.
- 24 VDC DIN power supply.
- HV contactor.
- HV terminal block.
- Required grounding/bonding hardware.

## Current Firmware Pin Map

| Function | ESP32 GPIO | Electrical interface |
| --- | ---: | --- |
| Door reed input | GPIO22 | Dry contact to GND, internal/external pull-up |
| Contactor aux closed | GPIO32 | 24 V field input through opto/input conditioner |
| High-limit trip/status | GPIO33 | 24 V field input through opto/input conditioner |
| Bench DS18B20 data | GPIO26 | 3.3 V OneWire |
| Ceiling DS18B20 data | GPIO27 | 3.3 V OneWire |
| Contactor coil MOSFET | GPIO13 | Low-side MOSFET gate/driver |
| LED red MOSFET PWM | GPIO16 | Low-side MOSFET gate/driver |
| LED green MOSFET PWM | GPIO17 | Low-side MOSFET gate/driver |
| LED blue MOSFET PWM | GPIO18 | Low-side MOSFET gate/driver |
| LED white MOSFET PWM | GPIO19 | Low-side MOSFET gate/driver |
| Panel UART TX | GPIO14 | Direct 3.3 V UART to panel connector |
| Panel UART RX | GPIO4 | Direct 3.3 V UART from panel connector |

Avoid GPIO0, GPIO2, GPIO12, and GPIO15 for external field wiring because they
are ESP32 boot strap pins. Leave GPIO1/GPIO3 available for the dev board USB
serial path.

## Preferred Board Architecture

### ESP32 Carrier

Use two 19-pin female header rows for the existing ESP32 DevKitC v4 /
DevKitC-32E dev board. This keeps the firmware and known-good module unchanged,
avoids first-revision RF/module layout issues, and lets the controller be
removed for debugging.

The ESP32 socket headers should be vendor-installed if possible. Hand-soldering
38 closely spaced header pins is avoidable, and bad joints on the MCU carrier
would be painful to troubleshoot later.

Design requirements:

- Match the exact ESP32 DevKitC v4 footprint currently installed.
- Use two 1x19 female socket/header strips.
- Expose EN/BOOT enough that flashing/debugging is not blocked.
- Leave USB connector accessible after the dev board is installed.
- Power the dev board through its `5V` and `GND` header pins during normal
  operation.
- Avoid powering from both USB and board-supplied 5 V at the same time unless
  the PCB intentionally includes power isolation for that case.
- Add silkscreen labels for every used GPIO near the carrier pins.
- Consider a keyed outline or keepout so the dev board cannot be inserted
  offset by one pin without being obvious.

### Power

Use one 24 VDC input from the existing DIN supply.

Recommended rails:

- `+24V_IN`: from DIN supply.
- `0V`: common low-voltage return.
- `+5V`: generated on-board for ESP32 VIN and panel power.
- `+3V3`: provided by ESP32 dev board; use only for light sensor/input loads.

Open decision:

- Use a prebuilt DC/DC buck module footprint, or use an assembled SMD buck
  regulator circuit.

Practical first-revision bias:

- If hand assembly is likely: use a proven through-hole buck module footprint.
- If ordering assembled: use a PCB-assembly-friendly SMD buck design, but only
  after choosing parts that the assembler can source and place.

Target sizing:

- ESP32 dev board: budget at least 500 mA peak at 5 V.
- Panel/CrowPanel connector: budget separately; initial board target should
  probably reserve 1.5 A to 2 A at 5 V for panel power unless measured current
  says otherwise.
- Total 5 V converter target: tentatively 3 A minimum.

### Fusing and Protection

The new board should replace the low-voltage DIN fuse holders. The 24 V supply
and high-voltage protection remain external, but branch protection for board-fed
loads should be integrated.

Recommended protected branches:

| Branch | Protected load | Initial sizing note |
| --- | --- | --- |
| Board/control 24 V | PCB electronics upstream of buck/input circuits | TBD after schematic |
| 5 V rail | ESP32 and panel power | Size for selected buck and panel current |
| Contactor coil | 24 V coil control loop | Depends on measured/datasheet coil current |
| LED 24 V | RGBW LED strip common positive | 40 W practical max is about 1.7 A at 24 V; choose margin after wiring review |

Protection options to compare:

- PCB-mounted carriers for replaceable 5x20 mm cartridge fuses.
- Resettable PTC fuses for low-current/control branches.
- A combination: 5x20 mm cartridge fuses for LED/coil/primary branches, PTCs
  for small logic/sensor branches if useful.

Design requirements:

- Fuse/protection parts must be easy to inspect and replace with the board
  installed.
- 5x20 mm fuse carriers should be accessible without removing the PCB from the
  enclosure.
- Silkscreen should show fuse purpose and rating.
- LED branch protection must match the terminal and copper current rating.
- Coil branch protection must account for coil inrush and flyback/suppression.
- The manual-reset high-limit remains in the coil safety loop; PCB fusing does
  not replace that safety device.

### MOSFET Outputs

Use five low-side switched outputs.

| Output | Load | Firmware pin | Current class |
| --- | --- | ---: | --- |
| Coil sink | 24 V contactor coil negative | GPIO13 | Low current, inductive |
| LED R sink | RGBW strip red negative | GPIO16 | High current PWM |
| LED G sink | RGBW strip green negative | GPIO17 | High current PWM |
| LED B sink | RGBW strip blue negative | GPIO18 | High current PWM |
| LED W sink | RGBW strip white negative | GPIO19 | High current PWM |

Design requirements:

- Use SMD MOSFETs.
- Logic-level MOSFETs that switch fully at 3.3 V gate drive.
- Gate resistors and gate pulldowns.
- Flyback protection for the contactor coil output.
- Adequate PCB copper and terminals for LED current.
- Thermal margin at sauna-enclosure ambient temperatures.
- Clearly separate LED high-current returns from ESP32/input return until the
  board's intended common return point.

Open current questions:

- Actual contactor coil steady current and inrush.
- LED strip max measured/practical load is about 40 W total, about 1.7 A at
  24 V before design margin.
- Maximum expected current per RGBW channel, if one channel can dominate.

### Status Indicators

Add service/debug indicator LEDs where they help troubleshooting without
cluttering the board.

Recommended indicators:

- `5V` rail present.
- `24V` input present.
- `FAULT` indicator, driven by an ESP32 GPIO only if a spare safe GPIO is
  intentionally assigned in firmware.
- Output indicators for coil and/or RGBW channels if they do not materially
  complicate routing or load the GPIOs.

Open firmware decision:

- The current firmware does not assign a dedicated fault LED GPIO. Any hardwired
  fault indicator needs a firmware pin assignment, or it should be omitted from
  the first PCB.

### Inputs

#### Door Reed

The current firmware expects a dry contact input on GPIO22 with pull-up logic.

Recommended board interface:

- 2-pin field terminal: `DOOR` and `0V`.
- External pull-up option to 3.3 V, even if firmware also enables internal pull-up.
- Small series resistor and ESD/RC filtering footprint.

#### Contactor Aux Feedback

The current firmware expects GPIO32 to read true when the aux contact is closed.
The existing wiring assumes an opto input that pulls the GPIO low.

Recommended board interface:

- 2-pin or 3-pin field terminal for a 24 V wetting circuit through the aux contact.
- Optocoupler or digital input isolator/conditioner.
- Input resistor sized for 24 VDC.
- GPIO-side pull-up to 3.3 V.
- Silkscreen should state active polarity.

#### High-Limit Feedback

The high-limit must remain a hardware safety in series with the contactor coil.
The feedback input is diagnostic only.

Recommended board interface:

- Keep the SRL250/manual reset device in the coil safety loop.
- Add a diagnostic sense input that reports whether the high-limit path is open.
- Use opto/input conditioning for any 24 V sense into GPIO33.

Open decision:

- Sense voltage across the high-limit device, or sense the post-high-limit
  coil-positive node. The firmware polarity should be verified against the
  final circuit before fabrication.

### DS18B20 Temperature Inputs

Use two independent OneWire connectors.

Each connector:

- `3V3`
- `DATA`
- `0V`

Board details:

- 4.7 kOhm pull-up from DATA to 3.3 V on each bus.
- Optional ESD protection footprint.
- Terminal or locking connector suitable for field probe wiring.
- Label connectors as `BENCH` and `CEILING`.

### Panel Connector

The panel electronics are out of scope. The controller board only needs a cable
landing point.

Minimum connector signals:

- `+5V_PANEL`
- `0V`
- Controller UART TX from GPIO14.
- Controller UART RX to GPIO4.

The panel cable is short, so the design no longer needs RS-485 conversion for
the current installation. The board should expose direct 3.3 V UART-level
signals and 5 V panel power through the RJ45 panel connector.

Optional future-proofing:

- Add unpopulated pads or a small expansion footprint for RS-485 if desired,
  but do not make RS-485 part of the required first board.

## Connector Draft

Terminal labels should match enclosure wiring labels.

| Connector | Signals |
| --- | --- |
| 24 V input | `+24V_IN`, `0V_IN` |
| 5 V panel output | `+5V_PANEL`, `0V_PANEL` |
| Coil loop/control | `COIL+_SAFE`, `COIL-` or equivalent final loop labels |
| LED output | `LED_V+`, `LED_R-`, `LED_G-`, `LED_B-`, `LED_W-` |
| Door | `DOOR`, `0V` |
| Aux feedback | `AUX_24V`, `AUX_RETURN/SENSE` |
| High-limit feedback | final sense terminals TBD |
| Bench temp | `3V3`, `DATA`, `0V` |
| Ceiling temp | `3V3`, `DATA`, `0V` |
| Panel comms | `+5V_PANEL`, `0V_PANEL`, `PANEL_TX`, `PANEL_RX` |

## Physical Layout Priorities

Wiring cleanliness is a primary design requirement. Connector placement should
be organized by external hookup/cable, not by internal electrical function.

For example, the LED connector should contain `LED_V+`, `LED_R-`, `LED_G-`,
`LED_B-`, and `LED_W-` together in one physical group. Do not place LED power
near the power input and LED channel returns somewhere else. The same rule
applies to the panel, temperature probes, door input, coil/control loop, and
feedback inputs.

### Connector Grouping Principle

Each external device or field cable should land in one obvious board area:

| External hookup | Connector grouping goal |
| --- | --- |
| 24 V supply feed | One 2-pin input block: `+24V_IN`, `0V_IN` |
| RGBW LED strip cable | One grouped 5-position block: `LED_V+`, `LED_R-`, `LED_G-`, `LED_B-`, `LED_W-` |
| Contactor coil/control wiring | One grouped block for the final coil loop/control terminals |
| Door reed switch | One 2-pin block: `DOOR`, `0V` |
| Contactor aux feedback | One grouped input block for aux wetting/sense wiring |
| High-limit feedback | One grouped input block for high-limit sense wiring |
| Bench temp probe | One 3-pin block: `3V3`, `DATA`, `0V` |
| Ceiling temp probe | One 3-pin block: `3V3`, `DATA`, `0V` |
| Panel cable | One grouped block: `+5V_PANEL`, `0V_PANEL`, `PANEL_TX`, `PANEL_RX` |

Terminal blocks should be chosen for the actual field wiring, which is a mix of
18 AWG and 22 AWG. Use pluggable or fixed screw/spring terminal blocks with:

- Current rating above the protected branch rating.
- Wire range that comfortably accepts 18 AWG for LED/24 V/high-current wiring.
- Wire range that still clamps 22 AWG sensor/control wiring reliably.
- Pitch large enough to wire cleanly in the enclosure.
- Orientation that lets wires enter from the board edge without crossing over
  the ESP32 or other connector groups.

Fuse carriers are also user-facing service parts. Place the 5x20 mm carriers
as a clean grouped row or service zone near the power/high-current connector
area, with enough finger/tool clearance to remove a fuse without disturbing
field wiring.

### Board Edge Plan

Initial placement bias:

- Put all field wiring connectors along one or two board edges, facing outward
  toward enclosure wire duct or DIN terminal space.
- Group high-current 24 V/LED/coil connectors together, but keep them physically
  distinct from sensor and GPIO-level connectors.
- Put low-current field inputs and temperature probe connectors together in a
  labeled "inputs/sensors" area.
- Put the panel connector near the logic side of the board, but still as one
  complete cable landing point.
- Put the ESP32 dev board where its USB connector remains accessible without
  crossing field wiring.
- Keep the 24 V to 5 V converter close to the 24 V input and 5 V distribution,
  while preserving the external connector grouping above.

### Mechanical Target

Initial physical target:

- Board size around 130 mm x 85 mm if the connector/fuse layout remains clean.
- Four M3 mounting holes, one near each corner.
- Mount to the existing enclosure backplate.
- Enclosure context is approximately 500 mm x 400 mm x 200 mm, so the board
  should not be over-compressed at the expense of labeling and service access.
- Preserve ESP32 USB/programming access as much as practical.
- Preserve reasonable clearance around the ESP32 module antenna area.

### Silkscreen and Usability

The board should be easy to wire correctly while mounted in the enclosure.

Required markings:

- Large connector group labels: `POWER`, `LED`, `COIL`, `DOOR`, `AUX`,
  `HIGH LIMIT`, `BENCH TEMP`, `CEILING TEMP`, `PANEL`.
- Per-terminal labels next to every terminal, readable after installation.
- Polarity labels for `+24V`, `+5V`, `3V3`, and `0V`.
- Active-state labels for diagnostic inputs where helpful, for example
  `AUX CLOSED = ON`.
- GPIO labels near ESP32 carrier pins for debugging.

### Layout Tradeoffs

This grouping requirement may make some internal routing longer. That is
acceptable for low-speed GPIO, OneWire, and UART signals. For high-current LED
and coil paths, the board should instead place the MOSFETs and current-handling
traces close to their grouped output connector so the external wiring stays
clean without forcing long high-current paths across the board.

## Assembly Strategy Options

### Option A: Mostly Through-Hole / Hand Assembly

Pros:

- Easier to inspect and rework.
- Terminal blocks, fuse holders, headers, and buck modules are straightforward.
- Lower risk for a first electronics project.

Cons:

- More manual soldering.
- Larger board.
- MOSFET thermal/layout quality still matters.
- ESP32 carrier headers have many pins to solder.

### Option B: Mixed Assembly

Have the PCB vendor assemble SMD parts such as MOSFETs, resistors, optos, ESD
parts, and buck regulator parts. Hand-solder large through-hole parts such as
terminal blocks and fuse holders.

Preferred update for this project: ask the vendor to install the two 1x19 ESP32
female headers as well. Those are mechanically large parts, but there are 38
joints and they are central to board reliability. If vendor-installed through-hole
headers are expensive or unavailable, use a local assembly service or soldering
fixture rather than making the ESP32 socket the first difficult hand-soldering
job.

Pros:

- Good balance for this board.
- Avoids hand-soldering many small parts.
- Avoids hand-soldering the 38-pin ESP32 socket if the vendor supports it.
- Keeps bulky mechanical parts flexible.

Cons:

- Requires choosing assembler-available parts and footprints.
- Some through-hole parts may still need manual work.

### Option C: Fully Assembled

Have the PCB vendor assemble as much as possible, including SMD electronics and
possibly compatible connectors/headers.

Pros:

- Cleanest repeatability.
- Less soldering.

Cons:

- Requires more precise BOM/footprint choices.
- Through-hole assembly can increase cost or be unavailable depending on vendor.
- Field terminal blocks may still be better hand-installed.

Practical first-revision recommendation: design for mixed assembly.

## Design Checks Before Ordering

- Measure the exact ESP32 dev board footprint and pin count.
- Measure available enclosure mounting area and standoff locations.
- Confirm LED strip current from label/datasheet or direct measurement.
- Confirm contactor coil current and whether the coil already has suppression.
- Decide exact on-board fuse/protection strategy and ratings.
- Decide on terminal block pitch and current ratings.
- Confirm 5 V panel voltage at the panel under load over the actual cable.
- Verify direct UART reliability over the actual short panel cable.
- Resolve whether the high-limit input polarity in comments, docs, and firmware
  all describe the same real circuit behavior before schematic capture.
- Draw a field wiring diagram before PCB layout.
- Run ERC/DRC in KiCad before fabrication.
- Order a small first batch and test with bench supplies/current limits before
  connecting the sauna loads.

## Likely CAD Workflow

Use KiCad for this project.

1. Create schematic from this requirements table.
2. Assign exact manufacturer part numbers and footprints.
3. Run electrical rules checks.
4. Lay out the board around connector placement and high-current paths first.
5. Keep logic/input conditioning away from LED current paths.
6. Add mounting holes, labels, test points, and keepouts.
7. Generate fabrication outputs: Gerbers, drill files, BOM, and pick-and-place.
8. Price the same design as bare PCB, mixed assembly, and fuller assembly.
