# PCB Rev B Notes

These notes capture lessons from ordering, assembling, and bringing up the first custom PCB. Treat the current board as Rev A/as-built. These are candidate changes for the next PCB spin, not instructions for modifying the installed board.

## Rev A Bring-Up Status

Working core functions:

- ESP32 DevKitC carrier/socket power and GPIO routing.
- 24 V input distribution and 24 V to 5 V conversion.
- Contactor coil low-side MOSFET drive.
- RGBW LED MOSFET outputs.
- Bench and ceiling DS18B20 temperature inputs.
- Door reed input.
- Panel 5 V power and direct UART.

Known issue under investigation:

- `Contactor Aux Closed` stays false/open even when the contactor closes.
- The contactor auxiliary block is wired to the normally-open `13/14` contacts.
- Meter readings confirmed that `13/14` close correctly and both sides rise to 24 V when the contactor is pulled in.
- Jumping/closing the AUX loop does not pull the PCB AUX terminals down to the expected optocoupler LED voltage.
- Current suspicion: Rev A `OPT_AUX1` input path issue, such as optocoupler orientation, soldering, wrong pinout, damaged opto, or missing input-side ground continuity.

Debug path for the installed Rev A board:

1. With board powered and AUX open, one AUX terminal should be about 24 V and the other may be near 0 V.
2. With AUX terminals shorted, both AUX terminals should drop to roughly 1.0-1.3 V if the optocoupler LED path is conducting.
3. If both stay at 24 V, inspect/rework `OPT_AUX1`, `R_OPT_AUX_LED1`, and the opto input-side ground connection.
4. If the AUX terminals drop correctly, probe `GPIO32`; it should move from about 3.3 V open to near 0 V active.
5. If directly pulling `GPIO32` to ground changes the ESPHome entity, firmware and ESP GPIO mapping are correct.

## Rev B Electrical / Connector Changes

### Coil, SRL250, and Aux Wiring

Rev A uses one 3-pin `COIL / SAFETY` connector:

- `+24V_COIL` out to SRL250.
- `HI_LIM_SENSE`, the return from SRL250 / contactor coil+ node.
- `COIL-`, the MOSFET-switched coil negative.

This works electrically, but the field wiring is less obvious than it should be.

Rev B should consider separating the safety loop and contactor coil into clearer connector groups:

- `J_SRL250`, 2-pin:
  - `SRL250_OUT`: fused +24 V from board to SRL250 input.
  - `SRL250_RETURN`: SRL250 output returning to the board.
- `J_COIL`, 2-pin:
  - `COIL+`: routed from `SRL250_RETURN` on the board.
  - `COIL-`: MOSFET-switched coil negative.

Alternative combined contactor connector:

- One 4-pin contactor connector near the contactor:
  - `COIL+`
  - `COIL-`
  - `AUX_A`
  - `AUX_B`

That would keep all contactor-local wires together while keeping the SRL250 field loop separate.

Preferred physical placement for Rev B:

- Move `J_SRL250` down near the bottom sensor/safety wiring area, beside temperature sensors and door input, because those wires come from the sauna side.
- Keep `J_COIL`, contactor aux, 24 V power input, and contactor-related power routing near the top/contactor side of the enclosure.
- Move the panel connector up or to a side edge if needed; the panel cable has more routing flexibility than the SRL250/sensor/door harnesses.

### AUX Input Review

Before Rev B layout:

- Verify the exact optocoupler symbol and footprint pin mapping for `OPT_AUX1` and `OPT_HL1`.
- Confirm the package orientation convention in KiCad, the assembly preview, and the physical parts.
- Add clearer silkscreen around the optocouplers: pin 1 dot/notch, input side, and output side.
- Consider adding two small probe pads for AUX input debugging:
  - AUX opto LED anode/return node.
  - `GPIO32`.
- Consider whether contactor aux should be a simpler dry-contact input referenced to board ground instead of a 24 V opto loop. The opto loop is more isolated and robust, but a dry-contact-to-ground input would be simpler if the aux wiring is short and entirely inside the low-voltage cabinet.

## Rev B Mechanical / Layout Changes

### Fuse Holder Footprint

Rev A used the KiCad Schurter OG 5x20 fuse clip footprint:

- `Fuseholder_Clip-5x20mm_Schurter_OG_Lateral_P15.00x5.00mm_D1.3mm_Horizontal`

This did not match the actual fuse clips purchased. The board holes are rotated/mismatched relative to the received clip geometry.

Rev B requirements:

- Pick the exact fuse clip or holder before layout.
- Use the manufacturer footprint or create a custom footprint from the datasheet.
- Print a 1:1 paper footprint and physically test the actual fuse clips before ordering.
- Consider a more integrated/top-access 5x20 fuse holder instead of loose clips if it improves serviceability and reduces footprint ambiguity.

### Fuse / Coil Connector Spacing

The coil fuse holder area is too tight relative to the coil/safety connector.

Rev B requirements:

- Increase clearance around the coil fuse holder for finger/tool access.
- Keep fuse replacement paths clear of terminal block wire exits.
- Separate fuse holders from tall terminal blocks enough that fuses can be inserted/removed with wiring installed.
- Preserve clear silkscreen fuse labels and fuse rating labels.

### Harness-First Connector Placement

Rev B should place connectors by real harness entry and service workflow:

- Bottom / sauna-entry side:
  - Bench DS18B20.
  - Ceiling DS18B20.
  - Door reed.
  - SRL250 to/from connector.
- Top / DIN-contactor side:
  - 24 V power input.
  - Contactor coil connector.
  - Contactor aux connector or combined coil+aux connector.
  - LED output if that harness exits near the contactor/power side; otherwise keep with the cable-gland side.
- Side or top:
  - Panel connector, because the panel cable has more flexibility and is less tied to the sensor/safety harness grouping.

## Rev B Power Architecture Option

Rev A keeps the AC-to-24 V PSU external and integrates only 24 V distribution plus 24 V to 5 V conversion.

Rev B may integrate the 120 VAC to 24 V PSU onto the controller board while keeping the 240 VAC heater switching on the external contactor.

Potential benefits:

- Cleaner cabinet with fewer DIN-rail low-voltage components.
- One controller board handles low-voltage supply, fusing, distribution, logic, and field wiring.
- Less cabinet point-to-point wiring.

Important constraints:

- This would bring mains voltage onto the PCB and changes the safety/regulatory/routing burden substantially.
- Keep the 240 VAC heater current path off-board and on the contactor.
- Use a certified enclosed or PCB-mount AC/DC module, not a discrete offline supply design.
- Maintain required creepage/clearance, fuse selection, line/neutral labeling, earth/bonding strategy, and enclosure strain relief.
- Add slots/keepouts and a clear LV/HV boundary if mains is on the PCB.
- Treat this as a meaningfully different board class and review it more conservatively.

Power sizing update:

- The 24 V supply likely does not need the original 120-150 W class supply.
- Practical loads appear closer to 50-60 W:
  - RGBW LED strip about 40 W practical max.
  - Contactor coil expected to be modest, confirm from datasheet or measurement.
  - ESP32/panel/logic are comparatively small.
- Rev B target could be a 24 V supply in the 60 W class with margin, pending measured contactor coil current and panel current.

## Documentation Updates Before Rev B Ordering

Before another PCB order:

- Update the schematic values to match actual ordered parts, especially `C_5V_IN1 = 10uF/50V`.
- Replace all remaining old 10x38 fuse references with final 5x20 holder/fuse part numbers.
- Update fuse holder footprint and Digi-Key/Mouser buy list together.
- Update connector labels and wiring diagrams for the SRL250/coil split.
- Add an explicit field wiring diagram showing:
  - SRL250 loop.
  - Contactor A1/A2.
  - Aux contact `13/14`.
  - PCB terminal names.
- Record the final working panel terminal pinout and crossed TX/RX wiring.
