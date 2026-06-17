# Safety

This project is for **convenience control only**. It can command a contactor,
read sensors, manage lighting, and expose controls through Home Assistant or a
wall panel. It is not a primary safety system.

## Requirements

- Use a sauna heater that already includes its required safety systems.
- Keep the heater's listed/manual-reset high-limit and required thermal
  protections in place.
- Use UL/ETL/listed components where applicable, including the contactor, power
  supply, enclosure, terminal blocks, fuses/breakers, conductors, and glands.
- Size conductors, fuses, breakers, contactors, terminals, and enclosures for
  the actual heater load and installation environment.
- Keep high-voltage and low-voltage wiring physically separated.
- Bond and ground the enclosure and heater according to local code.
- Have the final design, enclosure, wiring, overcurrent protection, grounding,
  and installation reviewed and installed by a qualified electrician.

## Do Not Rely On

Do not rely on any of the following as life-safety equipment:

- ESPHome firmware
- Home Assistant
- WiFi
- The wall panel
- The custom carrier PCB
- Software temperature limits
- Relay feedback monitoring

The manual-reset high-temp loop and the heater's own listed safety systems must
remain the safety backstop.

## Design Intent

The control board should fail with the heater off when the ESP32 reboots,
firmware crashes, WiFi drops, Home Assistant is unavailable, or the wall panel
is unplugged. That fail-off behavior is useful, but it still does not make the
project a code-approved primary safety system.
