# Alex's Super Sauna Commander — PCB Layout Plan (v3, as-built)

> **Rev B planning:** The first manufactured PCB is installed and core
> functions are working. Post-install findings and candidate next-revision
> changes are tracked in `../../docs/PCB-REV-B-NOTES.md`.
>
> **As-built deviations from v2 plan (locked 2026-04-30):**
>
> - **Project name:** "Alex's Super Sauna Commander" (not "Sauna Controller"). Front and back silk both carry this name.
> - **F1 (LED branch fuse):** Reduced from 7.5 A T to **5 A T** (slow-blow, 5×20 mm). Actual LED current is ~2 A typ; 5 A gives 2.5× margin and faster fault response than 7.5 A.
> - **Panel connector:** RJ45 8P8C → **4-pin Phoenix MKDS terminal block** (TX, RX, +5V, GND). Cable is still **Cat6, but the RJ45 plugs are removed at both ends** — wires land directly in screw terminals at controller and panel. This drops the magnetics, the RJ45 shield network (1 nF + 1 MΩ), and simplifies the panel-side electronics.
> - **J_LED1 pin order:** Reordered from `V+, R−, G−, B−, W−` to **`R−, G−, B−, W−, 24V+`** so the high-current 24V wire lands at the end of the connector instead of the middle. Schematic and PCB both updated.
> - **Hi-limit thermostat label:** Silk reads `SRL250` (was briefly `SL250` due to typo).
> - **Fuses:** 10×38 mm → **5×20 mm cartridge** (Phase 4 captured this; no further change).
>
> The body of this plan still describes the original v2 design intent. Where it conflicts with the deviations above, the deviations win.

---

Plan for translating the (now ERC-clean) schematic into a manufacturable PCB ready for JLCPCB. Updated after Codex review surfaced critical issues — particularly that **the schematic is not as complete as v1 of this plan implied** (panel ESD, RJ45 shield network, and ESD parts for 3.3 V lines are still missing) and **the 10×38 mm fuse holder part identification is still TBD**.

## Context

**Schematic state:** 8 sections drafted, 0 ERC errors, 45 cosmetic warnings. 77 component instances in `pcb/sauna-controller.kicad_sch`. **Three deferred items must be added to the schematic before layout** — see Phase 1.

**Target output:** A `sauna-controller.kicad_pcb` file plus JLCPCB-ready manufacturing package (Gerbers including paste layers, drill files with map, CPL for SMD only, BOM with LCSC part IDs).

**Form factor:** 130×85 mm rectangular PCB, 4× M3 corner mounting holes (**non-plated by default** — chassis bonding stays on the DIN rail per the brief), 2-layer board, **2 oz outer copper (justified, see Phase 4)**, mounted to backplate inside 500×400×200 mm enclosure.

**Manufacturing:** JLCPCB. SMD components via PCBA service (mostly Basic Parts), through-hole hand-soldered.

## Honest constraint upfront — automation limits

- **Programmatic / file-edit (fast):** board outline, mounting holes, net classes / design rules, component placement at fixed coords, silkscreen text labels, basic copper pours
- **GUI / manual (reliable):** **all routing** (per Codex feedback — even "simple straight power traces" need GUI review on a mixed power/signal 2-layer board), component orientation fine-tuning, 3D render verification, DRC fixup

Auto-routers (freerouting et al.) are not reliable enough for this kind of board. Committing to GUI-only routing.

---

## Phase 1 — Schematic completion + cleanup (60 min, was 30)

**This phase is bigger than v1 of the plan stated.** Codex caught that several items I described as "deferred" are not yet in the schematic at all and **must be added before any layout work begins**.

### 1.1 Items to ADD (not just cleanup)

| Item | Status now | Action |
|---|---|---|
| USBLC6-2SC6 ESD on panel UART | NOT in schematic | Embed `USBLC6-2P6` (parent) + `USBLC6-2SC6` (extends) in lib_symbols. Add instance with TX/RX/+5V_PANEL connections. |
| RJ45 shield network (1 nF + 1 MΩ) | NOT in schematic | Add C_SHIELD (1 nF, 0805) and R_SHIELD (1 MΩ, 0805) between RJ45 shield pin and GND. Requires using an RJ45 symbol that has a shield pin (or adding the parts on a separate net). |
| Low-voltage ESD parts for 3.3 V lines | Currently `SMBJ30CA` placeholder (24 V standoff, way too high) | Replace `ESD_DR`, `ESD_DS_BENCH`, `ESD_DS_CEILING` with low-voltage ESD parts (~5 V standoff). Use `Diode:ESD9B5.0ST5G` (5 V working voltage, 0.85 pF capacitance — designed for 1-Wire and digital lines) in SOD-923 footprint. SMBJ30CA stays on the 24 V opto inputs (TVS_AUX, TVS_HL) where it's correct. |
| 14 test points | NOT in schematic | Add `Connector:TestPoint` symbols at each: +24V, +5V, +3V3, GND, LED_R-, LED_G-, LED_B-, LED_W-, COIL-, GPIO32, GPIO33, GPIO22, RJ_TX, RJ_RX. Footprint: `TestPoint:TestPoint_Pad_D1.5mm`. |

### 1.2 Cleanup items

| Item | Action |
|---|---|
| `Q_NMOS_GDS` lookup warning | Rename custom symbol to `sauna-controller:Q_NMOS_GDS` (project-local namespace) so it doesn't clash with stock `Device`. Update lib_symbols header and 5 instance lib_id references. |
| Section 5 off-grid coords | Move opto-related coords (`100.08` → `100.33`, `122.38` → `121.92`, `137.62` → `137.16`) by adjusting **symbol origins** (not via global string replace, which broke connectivity last time). Update connected wire endpoints together. |
| RJ45 footprint reference | Change `Connector_RJ:RJ45_Bel_Stewart_SS-7188NF-A40_Horizontal` to a footprint that actually exists in KiCad 10 stock library. Verified candidates to check: `RJ45_Wuerth_*`, `RJ45_Amphenol_*`, `RJ45_8P_Lancable_BS-25-001-*`. Pick one and update the footprint property. |

### 1.3 Verification

| Check | Action |
|---|---|
| AOD4184A pin mapping | **Before** ordering, verify symbol pin G=1, D=2, S=3 numbering matches both the AOD4184A datasheet (DPAK pin 1=G, pin 2/tab=D, pin 3=S) AND the stock `Package_TO_SOT_SMD:TO-252-2` footprint pad numbering. Verify by reading the .kicad_mod file directly: `grep '(pad ' TO-252-2.kicad_mod`. |

**Exit criteria:** ERC reports ≤5 warnings (only legitimate one-off label-uniqueness warnings). All schematic-side parts known to exist in PCB layout tools.

---

## Phase 2 — Footprint verification (30 min, was 60)

### 2.1 Fuse holder — switched to 5×20 mm (resolves the v1/v2 blocker)

**Decision (2026-04-29):** Use 5×20 mm cartridge fuses, not 10×38 mm. Reasons:
- 5×20 mm PCB-mount holders are abundantly stocked in KiCad's `Fuse.pretty` library and on JLCPCB. No custom footprint needed.
- 5×20 mm fuses are smaller, freeing PCB real estate.
- 5×20 mm 7.5 A slow-blow and 1 A fast-blow are standard parts widely available (Littelfuse, Schurter, Bel Fuse).

**Required fuses to purchase before bringing up the board:**
- F1: 5×20 mm **5 A T** (slow-blow, e.g., Littelfuse 0218005.MXP) — *was 7.5 A in v2; reduced to 5 A for tighter fault response, ~2.5× margin over 2 A typical LED current*
- F2: 5×20 mm 1 A F (fast-blow, e.g., Littelfuse 0217001.MXP)

**Footprint:** `Fuse:Fuseholder_Clip-5x20mm_Schurter_OG_Lateral_P15.00x5.00mm_D1.3mm_Horizontal` already referenced as placeholder in the schematic. Verify the choice during Phase 2.2 — possibly pick a more rugged variant like `Fuseholder_Clip-5x20mm_Keystone_3512_Inline_*` for top-loading replacement convenience.

### 2.2 Stock footprints — verified during plan review

| Symbol | Footprint | KiCad 10 stock library status |
|---|---|---|
| Resistors | `Resistor_SMD:R_0805_2012Metric` | ✅ in stock |
| Caps | `Capacitor_SMD:C_0805_*`, `C_1210_*` | ✅ in stock |
| Bulk cap | `Capacitor_THT:CP_Radial_D8.0mm_P3.50mm` | ✅ in stock |
| Diodes SMA/SMB/SOD-323 | `Diode_SMD:D_SMA`, `D_SMB`, `D_SOD-323` | ✅ in stock |
| AOD4184A MOSFET | `Package_TO_SOT_SMD:TO-252-2` | ✅ in stock; **verify pad numbering G=1, D=2, S=3** |
| LED 0805 | `LED_SMD:LED_0805_2012Metric` | ✅ in stock |
| LTV-817 | `Package_DIP:DIP-4_W7.62mm` | ✅ in stock (THT) |
| USBLC6-2SC6 | `Package_TO_SOT_SMD:SOT-23-6` | ✅ in stock |
| Phoenix terminal blocks (2/3/5 pos) | `TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-{2,3,5}-5.08_*_Horizontal` | ✅ in stock |
| ESP socket headers (1×19 female) | `Connector_PinSocket_2.54mm:PinSocket_1x19_P2.54mm_Vertical` | ✅ in stock |
| Polyfuse | `Resistor_SMD:R_1812_4532Metric` | ✅ in stock |
| RJ45 jack | **must change to stock — pick from `RJ45_Wuerth_*` or similar** (TBD) | ⚠️ current schematic name doesn't exist |
| ESD9B5.0ST5G | `Diode_SMD:D_SOD-923` | ✅ in stock (low-cap ESD) |
| Recom R-78E | `Converter_DCDC:Converter_DCDC_RECOM_R-78E-0.5_THT` | ✅ in stock (TO-220 footprint shared across R-78E variants) |
| TestPoint | `TestPoint:TestPoint_Pad_D1.5mm` | ✅ in stock |

### 2.3 Custom footprints

**None required.** The 5×20 mm fuse holder choice eliminates the only custom footprint that was planned. All footprints come from KiCad 10 stock libraries.

---

## Phase 3 — Board outline + mechanicals (15 min)

Programmatic. Edit `pcb/sauna-controller.kicad_pcb`:

- **Board outline (Edge.Cuts):** 130 × 85 mm rectangle with R5 rounded corners. Origin (0,0) → (130, 85).
- **Mounting holes:** 4× M3 (3.2 mm drill, 6 mm pad) at (5, 5), (125, 5), (5, 80), (125, 80). **Non-plated by default** (Codex feedback: chassis bonding is on the DIN rail per the brief; plated mounting holes would create accidental ground bonding to the enclosure backplate, which the brief deliberately avoids).
- **Antenna keepout zone:** 15 mm clearance on all sides of the WROOM-32E module's antenna end (Espressif Hardware Design Guidelines, "Positioning a Module on a Base Board"). The ESP socket orientation places the antenna end facing the open top edge of the PCB. Keepout zone defined on F.Cu, B.Cu, and inner layers (no copper, no traces, no components).
- **Layer stackup:** 2-layer, 1.6 mm FR4. **Outer copper 2 oz**, justified per Phase 4. Soldermask green, silkscreen white.

---

## Phase 4 — Net classes + design rules (10 min)

| Net class | Trace width | Via | Clearance | Nets |
|---|---|---|---|---|
| POWER_HV | 2.0 mm | 0.8 mm drill / 1.4 mm pad | 0.3 mm | +24V, +24V_LED, +24V_COIL, +24V_IN_RAW |
| POWER_LV | 0.5 mm | 0.6 mm / 1.0 mm | 0.2 mm | +5V, +5V_PANEL, +3V3 |
| GND | (single solid plane on B.Cu) | 0.6 mm / 1.0 mm | 0.2 mm | GND |
| LED_OUT | 1.0 mm | 0.6 mm / 1.0 mm | 0.2 mm | LED_R-, LED_G-, LED_B-, LED_W-, COIL- |
| SIGNAL | 0.25 mm | 0.4 mm / 0.8 mm | 0.15 mm | All GPIO, opto outputs, DS18B20, UART |

### Why 2 oz copper (justification, per Codex feedback)

IPC-2221 external trace formula: `I = 0.048 × ΔT^0.44 × A^0.725`.
- For 7.5 A on 2 oz copper, 2.0 mm trace: ΔT ≈ 14 °C — comfortable margin
- For 7.5 A on 1 oz copper, equivalent trace would need ~4.0 mm width — unworkable on a 130 mm board
- Cost: JLCPCB charges ~$5 per 5 boards for 2 oz upgrade — minor

2 oz is the right choice for this board's high-current section. Documented for the BOM.

---

## Phase 5 — Component placement (75 min, was 60)

Programmatic. Coordinates verified against actual footprint courtyards.

### Edge-zone strategy

| Edge | Connectors | Cable destination |
|---|---|---|
| Right edge | J_PWR, J_COIL, J_AUX | DIN-rail half of enclosure |
| Bottom edge | J_PANEL (RJ45), J_DOOR, J_CEILING, J_BENCH, J_LED | Cable glands → sauna interior |
| Top + left | (empty + status LEDs) | Mechanical clearance |

### Bottom-edge spacing fix (Codex feedback)

V1 had connectors at 12–20 mm center-to-center. Actual courtyard widths from KiCad stock footprints:
- `MKDS-1,5-2-5.08`: 18.36 mm wide (X span ≈ -3.04 to 15.32)
- `MKDS-1,5-3-5.08`: 23.44 mm wide
- `MKDS-1,5-5-5.08`: 26.40 mm wide (X span ≈ -3.04 to 23.36)
- RJ45 horizontal: ~22 mm wide (depends on footprint chosen)

Plus 3 mm clearance between adjacent footprints and 5 mm from board edge.

**Revised bottom-edge layout (left to right, all anchors on bottom edge y ≈ 78):**

| Connector | Anchor X | Notes |
|---|---|---|
| J_PANEL (RJ45) | 16 | 22 mm wide |
| J_DOOR (2-pos) | 38 | 18 mm wide |
| J_CEILING (3-pos) | 58 | 23 mm wide |
| J_BENCH (3-pos) | 81 | 23 mm wide |
| J_LED (5-pos) | 105 | 26 mm wide |

Spacing: ~3 mm gap between courtyards. Total bottom-edge usage: ~118 mm (within 130 mm − 5 mm margins each side = 120 mm available).

### Other placement (top, right, center, MOSFET column)

Same as v1 for now; will be detailed when Phase 5 begins. ESP socket centered around (52, 42) with 25.4 mm row spacing. MOSFETs in a column on the right at x ≈ 100. Optos / sensors on the left at x ≈ 15. Power/fuses across the top at y ≈ 12.

Antenna of WROOM-32E: faces the **top edge** (low y). 15 mm keepout means no copper or components within y < 15 mm of the antenna end. The top-edge power section needs to live x > 30 mm to leave the antenna zone clear. Need to verify ESP-DevKitC dev board orientation when placed (which header is closer to the antenna depends on dev board variant).

---

## Phase 6 — Routing (90 min, mostly GUI manual)

**No programmatic routing.** Codex feedback: don't try to script even simple traces on a mixed power/signal 2-layer board.

GUI workflow:
1. Lock placement first
2. Run kicad-cli pcb drc to confirm placement is clean before routing
3. Manual route in this order:
   a. **Power rails first:** 24 V from J_PWR through F1/F2/U1, +5V from U1 to ESP and RJ45, +3V3 from ESP J1 pin 1 to pullups
   b. **High-current returns:** LED_X- and COIL- traces from MOSFET drains to terminal blocks
   c. **GND plane:** copper pour on B.Cu, single contiguous plane (per Codex — drop the star-island idea)
   d. **Signal traces:** GPIO, opto outputs, DS18B20, UART
4. Add via stitching to GND plane in high-current and EMI-sensitive areas

### GND strategy (revised per Codex)

**Single solid GND plane on B.Cu.** No island splits. Manage high-current return paths via:
- Component placement (keep MOSFET sources close to where their associated terminal block grounds are routed)
- Trace width on the top layer where GND traces exist
- Via stitching density (more vias near MOSFET sources to give return current a low-impedance path back through the plane)

V1's "logic GND vs power GND" island plan was conceptually wrong for a 2-layer board and is dropped.

---

## Phase 7 — DRC + verification (20 min)

Use KiCad 10's `--schematic-parity` flag, not a manual netlist diff (which doesn't work the way v1 described).

```bash
# Schematic parity DRC — checks that PCB matches schematic
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc \
  --schematic-parity \
  --refill-zones \
  --output pcb/drc-report.txt \
  pcb/sauna-controller.kicad_pcb
```

**Pass criteria:**
- 0 errors. Warnings reviewed and accepted (or deferred with explicit acknowledgement).

### Visual review
- 3D render via `kicad-cli pcb render` or KiCad GUI to PNG
- Check clearances vs M3 mounting hardware, USB connector reach for flashing, terminal block screw access, RJ45 plug clearance

---

## Phase 8 — Silkscreen polish (30 min) — moved AFTER routing per Codex

V1 had silkscreen before routing; Codex correctly noted it should come after, since routing changes available silkscreen real estate. Rough labels go on during/before placement; final polish after routing finishes.

### Group labels (large)
`POWER`, `FUSES`, `5V CONV`, `COIL/SAFETY`, `AUX`, `LED OUT`, `BENCH`, `CEILING`, `DOOR`, `PANEL`

### Per-pin labels (small)
Each terminal pin: `+24V`, `0V`, `R−`, `G−`, `B−`, `W−`, `V+`, `DATA`, `3V3`, `TX`, `RX`, etc.

### ESP socket pin labels
GPIO number for each connected pin (e.g., `GPIO13` next to coil-driving pin)

### Project marking + decoration
- "SAUNA CTRL r1" top-left
- "← USB" pointer next to ESP USB end
- "ANTENNA →" + keepout marker near WROOM-32E antenna end
- Polarity markers (+, −) for polarized parts
- Diode cathode bands

---

## Phase 9 — Manufacturing output (30 min, was 15)

Per Codex feedback, JLCPCB requires more than v1 specified.

```bash
# Gerbers + paste layers + drill map (JLCPCB format)
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb export gerbers \
  --output pcb/output/ \
  --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts \
  --use-drill-file-origin \
  --subtract-soldermask \
  pcb/sauna-controller.kicad_pcb

# Drill files (Excellon format with metric units, plated/non-plated separated)
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb export drill \
  --output pcb/output/ \
  --excellon-separate-th \
  --excellon-units mm \
  --generate-map \
  --map-format pdf \
  pcb/sauna-controller.kicad_pcb

# Pick-and-place: SMD only (THT components hand-soldered)
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb export pos \
  --output pcb/output/cpl-smd.csv \
  --format csv \
  --units mm \
  --side both \
  --exclude-dnp \
  --smd-only \
  pcb/sauna-controller.kicad_pcb

# BOM with LCSC part numbers
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export bom \
  --output pcb/output/bom.csv \
  --fields Reference,Value,Footprint,LCSC \
  --group-by Value,Footprint \
  pcb/sauna-controller.kicad_sch
```

JLCPCB-specific conventions to verify:
- File extensions: JLCPCB accepts standard `.gbr` or Protel-style `.gtl/.gbl/.gts/.gbs/.gto/.gbo/.gko`. KiCad CLI default is `.gbr` — accepted.
- Drill: combined NPT + PT or separate. JLCPCB accepts both; we're using separate (`--excellon-separate-th`).
- Drill map: JLCPCB doesn't strictly require but it's good documentation.
- CPL: SMD-only file for PCBA. THT components don't go in CPL since they're hand-soldered.

**Then:**
- Zip `pcb/output/` for upload
- Upload, verify Gerber preview matches expectation
- Confirm PCBA component placements (ESP socket headers — verify 25.4 mm row spacing)
- Order 5 prototypes

---

## Risks / open items (post-Codex review)

| Risk | Severity | Mitigation |
|---|---|---|
| **10×38 mm PCB-mount fuse holder part not yet identified** | CRITICAL | User picks specific part with datasheet before Phase 2 starts |
| **Schematic completeness gap** (USBLC6, RJ45 shield, low-V ESD parts missing) | CRITICAL | Phase 1 expansion — all must be added before layout |
| AOD4184A pin mapping | important | Verified before Phase 5 placement, not at DRC |
| RJ45 footprint name mismatch | important | Updated to a stock-existing footprint in Phase 1.2 |
| Bottom-edge connector spacing | important | Revised in Phase 5 with actual courtyard widths |
| Star-ground island concept dropped | (not a risk anymore) | Single solid GND plane per Codex |
| Antenna keepout dimension | important | 15 mm minimum clearance per Espressif |
| Manufacturing output completeness | important | Phase 9 expanded with paste layers, drill map, SMD-only CPL |
| 2 oz copper cost | minor | ~$5 upcharge confirmed for 5 boards |
| Routing time estimate | minor | 90 min likely optimistic; reality may be 2–3 hr |

## Estimated effort (revised)

| Phase | Time | Mode |
|---|---|---|
| 1. Schematic completion + cleanup | 60 min | programmatic |
| 2. Footprints (incl. custom) | 60 min | programmatic + custom drawing |
| 3. Board outline + mechanicals | 15 min | programmatic |
| 4. Net classes / DRC | 10 min | programmatic |
| 5. Placement | 75 min | programmatic |
| 6. Routing | 90+ min | GUI |
| 7. DRC + parity | 20 min | programmatic |
| 8. Silkscreen | 30 min | programmatic |
| 9. Manufacturing output | 30 min | programmatic |
| **Total** | **~6.5 hours** | mostly programmatic, routing GUI |

## Files I'll create

- `pcb/sauna-controller.kicad_pcb` — main board file
- `pcb/footprints/sauna-controller.pretty/Fuseholder_10x38mm_PCB.kicad_mod` — custom fuse holder (after part is identified)
- `pcb/footprints/sauna-controller.pretty/fp-lib-table` — local library entry
- `pcb/output/` — manufacturing files
- `pcb/firmware-diff.yaml` — FAULT LED firmware addition (already created)
- `pcb/sauna-controller-3d.png` — 3D render preview

## Files I'll modify

- `pcb/sauna-controller.kicad_sch` — Phase 1 expansion (add USBLC6, RJ45 shield network, low-V ESD parts, test points; rename Q_NMOS_GDS; snap section 5 to grid; fix RJ45 footprint reference)
- `pcb/sauna-controller.kicad_pro` — net classes, design rules, library table

## User decisions (resolved)

1. ~~10×38 mm fuse holder part~~ → **switched to 5×20 mm fuses; user will buy 5×20 7.5A T + 1A F**
2. **2 oz copper upgrade** → defaulting to YES (justified by trace-width math; ~$5 per 5 boards)
3. **Non-plated mounting holes** → defaulting to YES (per Codex; chassis bonding stays on DIN rail per the brief)

If you want to override defaults #2 or #3, say so before Phase 4 (net classes / DRC).
