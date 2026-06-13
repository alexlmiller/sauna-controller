# Rev B PCB — "Alex's Super Sauna Commander"

Complete KiCad design for the Rev B controller board, generated from a single
machine-checked design database. Start with **`REV-B-DESIGN-REVIEW.md`** — it
documents every gap, inconsistency, and decision that shaped this board.

## Contents

| File | What it is |
|---|---|
| `REV-B-DESIGN-REVIEW.md` | Gap analysis of the existing Rev B planning + decisions |
| `FIRMWARE-CHANGES.md` | The 4 firmware edits the new board needs (LED GPIO remap etc.) |
| `sauna-rev-b.kicad_pro` | KiCad project (net classes / design rules) |
| `sauna-rev-b.kicad_sch` | Full schematic — 92 symbols, self-contained (no external libs) |
| `sauna-rev-b.kicad_pcb` | Placed **and routed** board — 96 footprints, 499 track segments, 62 vias, B.Cu GND plane, antenna keepout |
| `tools/design.py` | Single source of truth: nets, parts, pin→net map, placement |
| `tools/footprints.py` | Footprint geometry definitions |
| `tools/generate_schematic.py` | design.py → `.kicad_sch` |
| `tools/autoroute.py` | Grid maze router → `tools/routing.py` |
| `tools/generate_board.py` | design.py + routing.py → `.kicad_pcb` |
| `tools/check_board.py` | Verifier: courtyard overlap, copper clearance, keepout, full net connectivity |

Regenerate everything with:

```bash
pip install kiutils numpy
python3 tools/generate_schematic.py
python3 tools/autoroute.py        # writes tools/routing.py
python3 tools/generate_board.py
python3 tools/check_board.py      # must print "all checks passed"
```

## Board summary

- 130 × 85 mm, 2-layer, **2 oz outer copper**, 4× M3 non-plated corner holes.
- **Right edge** (the contactor sits to the right): `J_COIL`, `J_AUX` — coil
  drive and aux feedback land next to the relay with the shortest field wires.
- **Top edge**: `J_PWR` (24 V in) feeding a vertical bank of three top-access
  5×20 fuse holders (F1 LED 5 A T, F2 coil 1 A F, F3 logic 1 A F) with open
  finger clearance — fixes the Rev A fuse-access complaint.
- **Left edge** (upper, above the antenna keepout): `J_LED`
  (R−,G−,B−,W−,V+) — the LED strip cable exits left.
- **Bottom edge** (sauna-harness side): `J_PANEL`, `J_DOOR`, `J_BENCH`,
  `J_CEILING`, `J_SRL250` — SRL250 on the **right side** of the bottom edge,
  toward the coil/contactor corner, per `PCB-REV-B-NOTES.md`.
- ESP32 DevKitC socket (2× 1×19) center-left, antenna facing the left edge
  with a copper/part keepout zone, well away from the contactor EMI on the
  right; USB end open toward the board interior.
- Five AOD4184A low-side switches placed beside their connectors: the coil
  MOSFET clusters on the right by `J_COIL`; the four LED MOSFETs sit in the
  upper-left beside `J_LED` so the 1 mm return traces stay short; 24 V runs
  are 2 mm on 2 oz copper.
- Three LTV-817 opto inputs (AUX / high-limit / spare) with anti-parallel
  protection diodes, SMBJ30CA TVS, and debug test points — the Rev A AUX
  failure is addressed with verifiable polarity and probe pads.
- Solid GND plane on B.Cu; B.Cu trace usage deliberately penalized by the
  router to keep the plane intact.
- 15 test points; 24 V / 5 V presence LEDs; FAULT LED on GPIO23.

## Verification status — read before ordering

Machine-checked in this repo (all passing): courtyard overlaps, board
boundary, antenna keepout, per-net-class copper clearance, and single-island
connectivity for every net (including the GND plane stubs).

**Not yet done (requires KiCad locally — do all of these):**

1. Open the project in KiCad (7 or newer), run **ERC** on the schematic and
   **DRC** on the board, and fill zones (`B`). Review the GND plane fill for
   starved areas.
2. The generated board has **no schematic↔PCB cross-probing links** (the two
   files are built from the same database but KiCad doesn't know that). Run
   `Update PCB from Schematic` in dry-run mode to cross-check net parity, or
   treat `tools/check_board.py` as the parity authority.
3. **1:1 print test-fit**: Keystone 3517 fuse holders (this exact failure
   shipped on Rev A), MKDS terminal blocks, DevKitC on the 25.4 mm socket
   rows.
4. Verify LTV-817 and AOD4184A pin mapping against physical parts/datasheets.
5. Bench-test AUX/HL opto channels with a 24 V supply before installing.

## Known simplifications

- Footprints are drawn from datasheet dimensions in `tools/footprints.py`,
  not imported from KiCad's libraries — verify courtesy of the 1:1 print.
- Routing is rectilinear (grid router); aesthetics can be improved in the
  KiCad GUI freely — connectivity and clearances are already valid.
- Silkscreen is functional (group + per-pin labels); polish to taste.
