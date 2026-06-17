# Rev B Control Board PCB

Complete KiCad design for the Rev B sauna control board. The board carries an
ESP32 DevKitC V4, switches the low-voltage outputs, senses the low-voltage
inputs, distributes 24 V/5 V, and terminates the field wiring cleanly.

This board is part of a **convenience-control** project only. It does not
replace the heater's listed safety systems, required high-limit controls,
proper overcurrent protection, grounding, or code-compliant high-voltage
installation. Use UL/ETL/listed components where applicable and have the final
enclosure and wiring reviewed and installed by a qualified electrician.

For installation-level instructions, start with
[`../../docs/BUILD-WITH-CARRIER-PCB.md`](../../docs/BUILD-WITH-CARRIER-PCB.md).
For design rationale, see [`../../docs/DESIGN.md`](../../docs/DESIGN.md).

## Board Summary

- 120.76 x 88 mm, 2-layer, 1 oz outer copper, 5 mm corner radius, 4x M3 corner
  holes.
- ESP32 DevKitC V4 socket, using ESP32-WROOM-32E or ESP32-WROOM-32D only. Do
  not use WROVER DevKitC variants because Rev B uses GPIO16/GPIO17.
- 24 V input distribution, 24 V to 5 V conversion, and resettable PTC branch
  protection.
- Low-side MOSFET outputs for relay coil, RGBW LEDs, and optional AUX output
  hardware.
- Opto-isolated relay-feedback and high-temp status inputs.
- Separate DS18B20 buses for bench and ceiling sensors.
- Direct 3.3 V UART wall-panel connector with 5 V panel power.

## Connector Layout

The placement follows the cabinet wiring:

| Edge | Connectors | Reason |
|---|---|---|
| Top | `J_PWR`, `J_AUX_OUT` | 24 V PSU is above the board; AUX output can route with top-side low-voltage wiring |
| Left | `J_LED` | LED branch is the highest current low-voltage path, kept short |
| Bottom | `J_PANEL`, `J_DOOR`, `J_BENCH`, `J_CEILING`, `J_SRL250` | Sauna-room and panel wiring enters along the lower side |
| Right | `J_COIL`, `J_RELAY_FB` | Contactor sits to the right, so coil and monitor wiring stay short |

## Key Electrical Choices

- The contactor coil is low-side switched on the board, but heater power stays
  on the external contactor.
- The manual-reset high-temp loop is in series with the contactor coil and is
  also sensed through an opto input.
- Relay feedback uses the contactor auxiliary contact through an opto input.
- RGBW LED outputs are low-side switched and include gate-sensed activity LEDs.
- The optional AUX output is exposed by Rev B firmware as `AUX Output`.
- The on-board FAULT LED follows the firmware's latched fault state.
- The 5 V rail uses a K7805-2000R3 SIP-3 buck converter.
- The board uses a B.Cu ground plane and net classes defined in
  [`tools/design.py`](tools/design.py).

## Files

| File | Purpose |
|---|---|
| `sauna-rev-b.kicad_pro` | KiCad project and design rules |
| `sauna-rev-b.kicad_sch` | Generated schematic |
| `sauna-rev-b.kicad_pcb` | Hand-routed board generated from source plus captured routing |
| `tools/design.py` | Source of truth for nets, parts, pin mapping, and placement |
| `tools/routing.py` | Captured KiCad routing |
| `tools/footprints.py` | Local footprint geometry |
| `tools/generate_schematic.py` | Regenerates the schematic |
| `tools/generate_board.py` | Regenerates the PCB from design data and routing |
| `tools/import_routing.py` | Captures hand-routed traces from KiCad |
| `tools/generate_bom.py` | Regenerates assembly BOM |
| `tools/export_fabrication.py` | Regenerates BOM, CPL, Gerbers, drills, and upload zip |
| `tools/_repro_check.py` | Verifies generated board content matches the checked-in PCB |
| `tools/check_board.py` | Checks clearances and connectivity |
| `fabrication/` | Current fabrication and assembly outputs |

## Edit Workflow

Routing and final placement are edited in KiCad, then captured back into the
generator inputs. After KiCad edits:

```bash
cd pcb/rev-b
python3 -m venv .venv && .venv/bin/pip install kiutils numpy
.venv/bin/python tools/import_routing.py
.venv/bin/python tools/_design_diff.py
.venv/bin/python tools/_silk_diff.py
.venv/bin/python tools/_repro_check.py
.venv/bin/python tools/generate_board.py
.venv/bin/python tools/check_board.py
```

Before ordering, also run KiCad ERC/DRC locally with zones filled.

## Assembly Notes

The Rev B board is intended to be supplier-assembled, including terminal blocks,
ESP sockets, electrolytics, K7805 buck, and resettable PTCs. The generated
assembly files are in [`fabrication/`](fabrication/).

Current notable JLC/LCSC selections include:

- AOD4184A MOSFETs: `C99124`
- SS54 Schottky diodes: `C22452`
- SMBJ30CA TVS diodes: `C5331115`
- F1 LED PTC: `C719172`
- F4 AUX PTC: `C139284`

Verify stock, polarity, substitutions, and physical fit before ordering. Print
the board 1:1 and test-fit the DevKitC, terminal blocks, PTCs, K7805, SOP-4
opto parts, and electrolytic capacitors.

## Verification

Machine checks in this repo cover courtyard overlaps, board boundary, antenna
keepout, per-net-class copper/edge clearance, and single-island connectivity.

Before installing a fabricated board:

1. Inspect polarity, soldering, terminal labels, and ESP32 orientation.
2. Confirm 24 V input, 5 V output, and 3.3 V ESP rail with no field loads.
3. Bench-test relay-feedback and high-temp opto channels with 24 V.
4. Test each LED channel with a current-limited load.
5. Test contactor coil control before energizing the heater circuit.
