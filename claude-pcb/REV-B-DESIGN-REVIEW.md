# Rev B Design Review — Gap Analysis & Decisions

Review of everything captured for the Rev B board across `docs/PCB-PLANNING.md`,
`docs/PCB-REV-B-NOTES.md`, `pcb/plans/PCB-LAYOUT-PLAN.md`, `README.md`,
`PANEL-REQUIREMENTS.md`, and the firmware (`sauna-controller.yaml`,
`sauna-panel-wired.yaml`). Issues are ordered by severity. Each one ends with
the decision baked into the Rev B design in this folder.

---

## Critical issues found

### 1. The 5 V regulator is undersized (R-78E-0.5 = 500 mA)

`pcb/plans/PCB-LAYOUT-PLAN.md` Phase 2.2 specifies a **Recom R-78E-0.5**
(500 mA), but `docs/PCB-PLANNING.md` budgets **≥500 mA for the ESP32 alone plus
1.5–2 A reserved for the CrowPanel**, with a stated converter target of
"tentatively 3 A minimum". These two documents directly contradict each other.

Reality check: an ESP32-S3 CrowPanel with a 480×480 IPS backlight typically
draws 300–450 mA at 5 V, and the DevKitC peaks ~500 mA during WiFi TX bursts.
Combined worst case is ~1 A — **double** the R-78E-0.5 rating. Rev A likely
works because typical (non-peak) draw sits just under 500 mA, which is exactly
the kind of margin-free design that browns out the panel during a WiFi burst.

**Decision:** Rev B uses the **OKI-78SR-5/1.5-W36-C** (1.5 A, 7–36 V in,
pin-compatible SIP-3 / TO-220 footprint, no external compensation needed).
Same footprint as the R-78E family, so it remains a drop-in swap either way.

### 2. The AUX opto input never worked on Rev A — root-cause before copying it

`PCB-REV-B-NOTES.md` documents that `Contactor Aux Closed` stays false even
with confirmed-closed 13/14 contacts, and shorting the AUX terminals does not
pull them down to opto-LED voltage. That symptom (both terminals stay at 24 V)
means **no current flows through the opto LED branch at all** — consistent with
a reversed opto, an open LED series path, or a missing return to the 24 V
negative rail, *not* a GPIO-side problem.

**Decisions baked into Rev B:**
- The opto input circuit is drawn with explicit, verifiable polarity: fused
  +24 V wetting → AUX_A terminal → field contact → AUX_B terminal → series
  resistor → opto LED anode (pin 1) → opto LED cathode (pin 2) → GND. The LED
  return to GND is a dedicated trace, not an assumption about a shared plane.
- An anti-parallel diode (1N4148WS) across each opto LED protects against
  reversed field wiring instead of silently failing.
- Test points on the opto LED node (`TP_AUXIN`) and on `GPIO32`/`GPIO33`
  (exactly the two probe pads PCB-REV-B-NOTES asked for).
- Silkscreen pin-1 marking and `IN`/`OUT` side labels at each opto.
- The LTV-817 pin mapping used: pin 1 = anode, 2 = cathode, 3 = emitter,
  4 = collector (DIP-4, pin 1 at the dimple). **Verify against the physical
  parts before ordering** — this is the prime suspect for the Rev A failure.

### 3. Fuse clip footprint mismatch (the Rev A mechanical bug)

Rev A used the stock Schurter OG clip footprint and the purchased clips did
not match. `PCB-REV-B-NOTES.md` requires picking the exact part first.

**Decision:** Rev B specifies the **Keystone 3517** snap-in 5×20 mm fuse
holder (single-piece, top-loading — also addresses the "more integrated/
top-access" suggestion in the notes). The footprint in this design is drawn
from the Keystone 3517 drawing (two 1.3 × 2.8 mm slotted pads on 22.6 mm
centers, body 26.3 × 7.9 mm). **Per the Rev B notes: print 1:1 and test-fit
the physical part before ordering.** If you keep loose clips instead, replace
the footprint — do not assume.

### 4. High-limit sense polarity — now pinned down

`PCB-PLANNING.md` left "sense across the device vs. sense the post-high-limit
node" open, and the firmware comment on GPIO33 ("FALSE when tripped (opto
pulls high)") contradicts its own lambda (`return x;` → entity TRUE when GPIO33
is HIGH). The only circuit consistent with the firmware as written is:

> Opto senses **24 V presence at the post-SRL250 / coil+ node**. Normal
> (SRL250 closed): node is at 24 V → opto ON → GPIO33 LOW → trip = FALSE.
> Tripped (SRL250 open): node dead → opto OFF → pull-up takes GPIO33 HIGH →
> trip = TRUE.

**Decision:** Rev B hard-wires the HL opto across `SRL250_RTN` → GND on-board
(no extra field terminals needed — the sense node already lands on the board
via `J_SRL250`). Firmware needs no change; fix the misleading comment.

---

## Inconsistencies between documents

| # | Inconsistency | Resolution in Rev B |
|---|---|---|
| 5 | `PCB-LAYOUT-PLAN.md` body still places an **RJ45** panel jack and an RJ45 shield network (1 nF + 1 MΩ), but the as-built deviations replaced it with a 4-pin Phoenix block and direct UART | Panel connector is a **4-pin MKDS** (`+5V_PANEL, GND, TX, RX`). The RJ45 shield network is obsolete and dropped. The USBLC6-2SC6 ESD protector on TX/RX is kept — those lines still leave the enclosure. |
| 6 | `README.md` says panel comms are **RS-485 (SP3485)**; `PCB-PLANNING.md` and the as-built board use **direct 3.3 V UART** over the short Cat6 run | Rev B stays with direct UART (it is installed and working). An **unpopulated SOT-23-8 RS-485 footprint option was considered and rejected** — it adds routing burden for a transceiver the working install doesn't need; revisit only if UART proves unreliable. Update README. |
| 7 | `README.md` parts list still says **10×38 mm DIN fuses, 7.5 A LED fuse**; the as-built plan switched to **5×20 mm, 5 A T** | Rev B: F1 LED = **5 A T**, F2 coil = **1 A F**, F3 logic = **1 A F**. README needs the same update (`PCB-REV-B-NOTES.md` already flags the stale 10×38 references). |
| 8 | `PCB-LAYOUT-PLAN.md` lists `pcb/firmware-diff.yaml` (FAULT LED) as "already created" — **it is not in the repo**, and no fault-LED GPIO is assigned in firmware | Rev B routes a FAULT LED to **GPIO23** (free, no boot-strap role). It is harmless if firmware never drives it. GPIO25 stays reserved for the commented-out "Future Monitoring" opto input, which Rev B provides as a third, optionally-populated opto channel (`OPT_SPARE`). |
| 9 | Rev A's 3-pin `COIL / SAFETY` connector confused field wiring | Split per the Rev B notes: **J_SRL250** (2-pin, bottom edge with the sauna-side harness) and **J_COIL** (2-pin, top edge near the contactor), plus **J_AUX** (2-pin, top edge). The 4-pin combined alternative was rejected because the SRL250 loop physically routes with the sauna harness, not the contactor. |
| 10 | `C_5V_IN1` schematic value didn't match the ordered part | Rev B schematic value is **10 µF / 50 V** as the notes require. |

## Gaps — things no document had thought through

11. **No reverse-polarity protection on the 24 V input.** A swapped `+24V/0V`
    at J_PWR would destroy the board. Rev B adds a unidirectional TVS
    (SMBJ33A) *and* a series Schottky is not practical at 5 A+, so instead a
    **P-FET reverse-polarity guard was considered and rejected** (cost/heat at
    LED current); the chosen compromise is the TVS + clearly silkscreened
    polarity + the fuses, which blow on hard reversal. Documented so the
    tradeoff is explicit rather than accidental.
12. **No bulk capacitance spec for PWM LED load steps.** 4 PWM channels
    chopping ~2 A into a 5 m cable will bounce the 24 V rail. Rev B places
    **220 µF/50 V electrolytic at the LED fuse** plus 100 nF ceramics.
13. **Coil flyback never made it into any plan** even though PCB-PLANNING
    requires it. Rev B places an **SS54** freewheel diode across the coil
    terminals (cathode → COIL+) at the connector, plus the MOSFET's avalanche
    rating as backup.
14. **Door input had no defined conditioning.** Rev B: 10 k pull-up to 3V3,
    1 k series, 100 nF to GND, ESD9B5.0 — matches the "external pull-up
    option + RC + ESD" requirement in PCB-PLANNING.
15. **Mains-on-board option (120 VAC → 24 V):** the notes float it with heavy
    caveats. **Rejected for Rev B** — it changes the board's safety class for
    marginal cabinet tidiness. The right follow-up is downsizing the external
    DIN supply to a ~60 W unit (e.g., HDR-60-24) per the measured-load note.
16. **Power-rail indicators:** 24 V and 5 V presence LEDs added (PCB-PLANNING
    recommended them; the layout plan dropped them silently).

## Layout-driven improvement: LED PWM GPIO remap

With `J_LED` pin order fixed at `R-, G-, B-, W-, V+` (Rev A deviation) and the
DevKitC header order fixed at GPIO19, 18, 17, 16 (left to right toward the
USB end), the Rev A firmware mapping (R=16 … W=19) is a perfect reversal —
every gate trace would cross every other one on the board. **Rev B remaps the
channels in firmware instead: R=GPIO19, G=GPIO18, B=GPIO17, W=GPIO16.** The
four gate traces then run parallel with zero crossings. It is a four-line
edit in `sauna-controller.yaml` (see `FIRMWARE-CHANGES.md`); all PWM pins are
equivalent, so nothing else changes.

## Carried forward unchanged (validated, no issues found)

- 130 × 85 mm outline, 4× M3 **non-plated** corner holes, 2-layer, **2 oz**
  outer copper (IPC-2221 math in the layout plan checks out for 2.0 mm / 5 A).
- Single solid GND plane on B.Cu — no star islands.
- AOD4184A (TO-252) low-side switches, G=1 D=2 S=3, 100 Ω gate / 10 k pulldown.
- ESD9B5.0ST5G on all 3.3 V field lines; SMBJ30CA on 24 V opto inputs.
- 15 mm antenna keepout (Espressif guideline); ESP socket = 2× 1×19 female,
  25.4 mm row spacing; USB edge kept clear.
- Net classes: POWER_HV 2.0 mm / LED_OUT 1.0 mm / POWER_LV 0.5 mm /
  SIGNAL 0.25 mm.
- Harness-first connector placement from PCB-REV-B-NOTES (see below).
- Test points on every rail, every output, every debug-relevant GPIO.

## Rev B connector plan (harness-first, per PCB-REV-B-NOTES)

| Edge | Connectors (left → right) | Rationale |
|---|---|---|
| **Top** (DIN/contactor side) | `J_PWR` (24 V in), `J_COIL`, `J_AUX`, `J_LED` | Power, contactor, and LED harnesses come from the DIN half |
| **Bottom** (sauna-entry side) | `J_PANEL`, `J_SRL250`, `J_DOOR`, `J_BENCH`, `J_CEILING` | Sensor/safety/panel harnesses enter via the bottom glands; SRL250 moved here as the notes require |
| **Left** | ESP32 antenna keepout — no copper, no parts | RF |

Fuse row sits between the top connectors and board center with finger
clearance on all sides of each Keystone 3517 (fixes the Rev A coil-fuse
crowding complaint).

## Firmware pin map used (verified against `sauna-controller.yaml`)

| GPIO | Function | Rev B circuit |
|---:|---|---|
| 13 | Coil MOSFET gate | Q1 via 100 Ω |
| 19/18/17/16 | R/G/B/W gates (**remapped**, see above) | Q2–Q5 via 100 Ω |
| 22 | Door reed | RC + pull-up + ESD |
| 32 | Aux closed (opto, active-low) | OPT_AUX collector |
| 33 | High-limit (opto on SRL250_RTN) | OPT_HL collector |
| 26 / 27 | Bench / Ceiling 1-Wire | 4.7 k pull-ups + ESD |
| 14 / 4 | Panel UART TX / RX | series 100 Ω + USBLC6 |
| 25 | Future monitoring (commented out) | OPT_SPARE collector |
| 23 | **NEW: FAULT LED** (needs firmware assignment) | LED + 1 k |
| 0/2/12/15 | boot straps | unconnected |

## What's in this folder

- `sauna-rev-b.kicad_sch` / `.kicad_pcb` / `.kicad_pro` — full schematic and
  placed, routed board (KiCad 7 file format; opens cleanly in KiCad 7/8/9/10).
- `tools/` — the Python generators that built the files (reproducible:
  `python3 tools/generate_schematic.py && python3 tools/generate_board.py`).
- `README.md` — bring-up and pre-order checklist.

## Before ordering — non-negotiable checks

1. Open both files in KiCad, run **ERC** and **DRC with schematic parity**,
   and review the GND zone fill. These files were generated and
   machine-validated for syntax and net consistency, but not run through
   KiCad's own checkers in this environment.
2. **1:1 print** the board and test-fit: Keystone 3517 holders, MKDS blocks,
   the DevKitC on the socket footprint (issue #3 above exists because Rev A
   skipped this).
3. Verify LTV-817 pin-1 orientation against a physical part (issue #2).
4. Bench-test the AUX/HL opto channels with a 24 V supply **before** the board
   goes in the cabinet.
5. Update README.md / buy list (issues #6, #7) so docs stop drifting.
