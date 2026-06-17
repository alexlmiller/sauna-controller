# JLC BOM Match Review

> **Rev A reference only.** These LCSC/JLC part matches are for the **Rev A**
> board. Rev B uses different parts (resettable PTCs, K7805 buck regulator,
> updated terminal blocks); see [`../../../rev-b/`](../../../rev-b/) and
> `pcb/rev-b/fabrication/` for the current Rev B BOM. Kept for the auto-match
> gotchas, which still apply when ordering.

Reviewed file:

- `/Users/alex/Downloads/sauna-controller-jlc-bom-JLCPCB Assembly Order.xls`

Review date:

- 2026-04-30

## Summary

The JLC dry-run confirmed the most important gating item:

- `J_ESP_L1,J_ESP_R1` matched to `C319202`, a 1x19 2.54 mm through-hole female socket header.

However, JLC's automatic matching made several bad selections. The upload BOM has been updated to force explicit part numbers for the bad or missing matches.

Updated upload file:

- `pcb/fabrication/assembly/sauna-controller-jlc-bom.csv`

## Bad Auto-Matches Found

These should not be accepted from the first JLC match:

- `R_RX1,R_TX1`: JLC matched `C26010`, which is `3.3k`, not `33 ohm`.
- `R_DR_S1,R_GATE_B1,R_GATE_COIL1,R_GATE_G1,R_GATE_R1,R_GATE_W1`: JLC matched a Keystone connector, not a `100 ohm` resistor.
- `F3`: JLC matched a through-hole disposable fuse, not an 1812 resettable PTC.
- `C_BULK1`: JLC matched an SMT `C1812` part with source quantity `0`, not the radial electrolytic footprint.
- `LED_PWR1`: JLC matched a through-hole LED footprint, not an 0805 LED.
- `LED_COIL1`: JLC matched a global-sourcing LED with source quantity `0`; use the explicit 0805 LED part instead.
- `LED_FAULT1`: no match.
- Several resistor groups were left unmatched.

## Explicit Corrections Added

The BOM now forces these candidate part numbers:

- `C_24V1`: `C28323`, Samsung 1uF 50V 0805 MLCC.
- `C_5V_OUT1`: `C45783`, Samsung 22uF 25V 0805 MLCC.
- `C_DR1`: `C1790`, Samsung 100pF 50V C0G 0805 MLCC.
- `C_BULK1`: `C2960384`, HRK 100uF 35V radial electrolytic, D8xL12mm, 3.5mm pitch.
- `F3`: `C151168`, Littelfuse 1812 500mA resettable PTC.
- `LED_COIL1`: `C2296`, yellow 0805 LED used as amber/status.
- `LED_FAULT1`: `C2295`, red 0805 LED.
- `LED_PWR1`: `C2297`, green 0805 LED.
- `R_DR_PU1,R_DS_BENCH1,R_DS_CEILING1,R_LED_COIL1,R_OPT_AUX_LED1,R_OPT_HL_LED1`: `C17673`, 4.7k 1% 0805.
- `R_DR_S1,R_GATE_B1,R_GATE_COIL1,R_GATE_G1,R_GATE_R1,R_GATE_W1`: `C17408`, 100 ohm 1% 0805.
- `R_GPD_B1,R_GPD_COIL1,R_GPD_G1,R_GPD_R1,R_GPD_W1,R_OPT_AUX_PU1,R_OPT_HL_PU1`: `C17414`, 10k 1% 0805.
- `R_LED_FAULT1,R_LED_PWR1`: `C17513`, 1k 1% 0805.
- `R_RX1,R_TX1`: `C17634`, 33 ohm 1% 0805.

## Remaining Open Item

`C_5V_IN1` is still unresolved:

- Requirement: `22uF/50V`
- Footprint: `C_1210_3225Metric`
- First JLC match: no match

Do not silently substitute this part in the upload. The likely options are:

- Find an exact 22uF/50V 1210 JLC-available part in the JLC UI.
- Review whether changing to a stocked 10uF/50V 1210 part is electrically acceptable for the DC/DC input.
- Leave this one part unassembled and hand-solder a 1210 MLCC, if necessary.

## Re-Upload Instructions

Upload again using:

- `pcb/fabrication/sauna-controller-gerbers-drill.zip`
- `pcb/fabrication/assembly/sauna-controller-jlc-bom.csv`
- `pcb/fabrication/assembly/sauna-controller-jlc-all-pos.csv`

Then check:

- `J_ESP_L1,J_ESP_R1` still match to `C319202`.
- No resistor group is matched to a connector or wrong value.
- `F3` is an 1812 resettable PTC, not a through-hole fuse.
- `C_BULK1` is radial through-hole with 3.5 mm pitch.
- All three indicator LEDs are 0805 parts.
- `C_5V_IN1` is either intentionally resolved or intentionally not populated.

## Updated Upload Review - 2026-04-30

Reviewed file:

- `/Users/alex/Downloads/sauna-controller-jlc-review-bom-JLCPCB Assembly Order.xls`

Result:

- The explicit resistor, PTC, and LED part-number corrections were recognized.
- `J_ESP_L1,J_ESP_R1` still matched to `C319202`.
- The export is still not order-ready.

Important process issue:

- The downloaded file name suggests the human review BOM may have been uploaded instead of the upload BOM.
- The JLC export shows odd column interpretation, such as the uploaded `Footprint` field being populated from note text for some rows.
- For JLC upload, use only `sauna-controller-jlc-bom.csv`, not `sauna-controller-jlc-review-bom.csv`.

Remaining issues from the updated match:

- `C_5V_IN1`: still no match.
- `J_AUX1`: no match.
- `J_BENCH1,J_CEILING1,J_COIL1`: no match.
- `J_LED1`: no match.
- `J_PANEL1`: no match.
- `U1`: no match.
- Many key matched parts show quantity/source as `0`, including:
  - SS54 diodes
  - SMBJ30CA TVS parts
  - SOD-323 ESD parts
  - fuse holders
  - ESP socket headers
  - optocouplers
  - MOSFETs
  - resistor groups

Interpretation:

- The part IDs are mostly correct, but the current JLC match export should not be approved.
- Re-upload using the dedicated JLC upload BOM and verify that the matched order quantities are nonzero for every part intended for assembly.

## Latest Upload Review - 2026-04-30 14:48

Reviewed file:

- `/Users/alex/Downloads/sauna-controller-jlc-bom-JLCPCB Assembly Order.xls`

Extracted review CSV:

- `pcb/fabrication/assembly/sauna-controller-jlc-latest-matched-export.csv`
- `pcb/fabrication/assembly/sauna-controller-jlc-latest-issues.csv`

Result:

- The correct JLC upload BOM appears to have been used this time.
- The explicit part-number fixes are recognized.
- Estimated component total shown in the export: `$22.9867` for 5 assembled boards, but this excludes rows still sitting at quantity/source `0`.

Good matched rows with nonzero quantity:

- `C_24V1`: `C28323`
- `C_5V_OUT1`: `C45783`
- `C_BULK1`: `C2960384`
- `C_DR1`: `C1790`
- `F3`: `C151168`
- `J_PANEL1`: `C122715`
- `LED_COIL1`: `C2296`
- `LED_FAULT1`: `C2295`
- `LED_PWR1`: `C2297`
- `U1`: `C22371890`
- `J_LED1`: `C8459`, but source quantity is only `1 JLCPCB`; verify whether JLC can supply enough before approving.

Rows matched but still unconfirmed/not included:

- `D_B1,D_COIL1,D_G1,D_R1,D_REV1,D_W1`: `C22452`
- `D_TVS_IN1,TVS_AUX1,TVS_HL1`: `C5331115`
- `ESD_DR1,ESD_DS_BENCH1,ESD_DS_CEILING1,TVS_5VP1,TVS_RX_PANEL1,TVS_TX_PANEL1`: `C2827694`
- `F1`: `C3204125`
- `F2`: `C3204125`
- `J_AUX1`: `C8383`
- `J_DOOR1`: `C8383`
- `J_PWR1`: `C8383`
- `J_BENCH1,J_CEILING1,J_COIL1`: `C49238`
- `J_ESP_L1,J_ESP_R1`: `C319202`
- `OPT_AUX1,OPT_HL1`: `C160821`
- `Q_B1,Q_COIL1,Q_G1,Q_R1,Q_W1`: `C99124`
- all resistor groups: `C17673`, `C17408`, `C17414`, `C17513`, `C17634`

These rows have the correct-looking part IDs, but the export shows `Qty 0.0` and `Source 0 JLCPCB`. They must be confirmed/selected in the JLC UI and then re-exported/rechecked.

Still no match:

- `C_5V_IN1`, 22uF/50V, 1210.

Do not approve the order until:

- `J_ESP_L1,J_ESP_R1` show nonzero quantity/source.
- all intended SMD and through-hole parts show nonzero quantity/source or are intentionally marked unassembled.
- `C_5V_IN1` is resolved or intentionally excluded.

## Final Match Check - 2026-04-30 14:52

Reviewed file:

- `/Users/alex/Downloads/sauna-controller-jlc-bom-JLCPCB Assembly Order (1).xls`

Extracted files:

- `pcb/fabrication/assembly/sauna-controller-jlc-finalcheck-matched-export.csv`
- `pcb/fabrication/assembly/sauna-controller-jlc-finalcheck-issues.csv`

Result:

- The latest match is substantially better.
- Matched parts now generally correspond to the intended component classes, values, and packages.
- `J_ESP_L1,J_ESP_R1` now show nonzero quantity/source: `C319202`, quantity `10`, source `10 JLCPCB`.
- Estimated component total shown in the export: `$53.8201` for 5 assembled boards.

Proper-looking matches:

- `C_24V1`: `C28323`, 1uF 50V 0805 MLCC.
- `C_5V_OUT1`: `C45783`, 22uF 25V 0805 MLCC, acceptable for the 10V rail requirement.
- `C_BULK1`: `C2960384`, 100uF 35V radial electrolytic, D8xL12mm, 3.5mm pitch.
- `C_DR1`: `C1790`, 100pF 50V C0G 0805 MLCC.
- `D_B1,D_COIL1,D_G1,D_R1,D_REV1,D_W1`: `C22452`, SS54 SMA Schottky diodes.
- `D_TVS_IN1,TVS_AUX1,TVS_HL1`: `C5331115`, SMBJ30CA SMB TVS parts.
- SOD-323 ESD group: `C2827694`, PESD5V0S1BA SOD-323 5V bidirectional ESD/TVS.
- `F3`: `C151168`, 1812 500mA resettable PTC.
- `J_ESP_L1,J_ESP_R1`: `C319202`, 1x19 2.54mm female headers.
- LEDs: `C2296`, `C2295`, `C2297`, 0805 yellow/red/green LEDs.
- `OPT_AUX1,OPT_HL1`: `C160821`, EL817(C)-G DIP-4 optocouplers.
- MOSFETs: `C99124`, AOD4184A TO-252.
- Resistor groups: correct 0805 values `4.7k`, `100`, `10k`, `1k`, `33`.
- `U1`: `C22371890`, R-78E5.0-1.0 compatible 5V 1A SIP DC/DC module.

Remaining blocker:

- `C_5V_IN1`: no match. Leave intentionally unpopulated for hand solder, or select a compatible 1210 MLCC. Do not use the checked electrolytic alternatives unless the PCB footprint is intentionally changed.

Remaining checks before approval:

- `J_LED1`: matched to `C8459`, but source shows `1 JLCPCB` while quantity is `5`; verify enough supply.
- `F1,F2`: verify Schurter fuse holder body and fuse insertion clearance.
- Terminal blocks: verify body style, wire-entry direction, and footprint fit.
- `U1`: verify pinout/lead spacing/height.
- `Q_*`: verify TO-252 pinout/rotation.
- All diodes/LEDs/ESD parts: verify polarity/orientation in JLC placement preview.

## Assembly-Only JLC BOM - 2026-04-30

Created files:

- `pcb/fabrication/assembly/sauna-controller-jlc-assembly-only-bom.csv`
- `pcb/fabrication/assembly/sauna-controller-jlc-assembly-only-pos.csv`
- `pcb/fabrication/assembly/sauna-controller-jlc-not-assembled-bom.csv`

Purpose:

- Have JLC assemble the ESP headers, SMD parts, optocouplers, DC/DC module, PTC, and radial bulk capacitor.
- Do not have JLC assemble the field terminal blocks, 5x20 fuse holders, or unresolved `C_5V_IN1`.

Validation:

- Assembly-only BOM: `20` grouped rows.
- Assembly-only designators: `56`.
- Assembly-only CPL placements: `56`.
- No BOM designators missing from CPL.
- No extra CPL designators.
- No blank JLC part numbers in assembly-only BOM.

Excluded from JLC assembly:

- `C_5V_IN1`
- `F1`, `F2`
- `J_AUX1`
- `J_DOOR1`
- `J_PWR1`
- `J_BENCH1`
- `J_CEILING1`
- `J_COIL1`
- `J_PANEL1`
- `J_LED1`

## Assembly-Only Match Check - 2026-04-30 16:46

Reviewed file:

- `/Users/alex/Downloads/sauna-controller-jlc-assembly-only-bom-JLCPCB Assembly Order.xls`

Extracted file:

- `pcb/fabrication/assembly/sauna-controller-jlc-assembly-only-matched-export.csv`

Result:

- The excluded parts are absent from the assembly quote:
  - `C_5V_IN1`
  - `F1`, `F2`
  - `J_AUX1`, `J_DOOR1`, `J_PWR1`
  - `J_BENCH1`, `J_CEILING1`, `J_COIL1`
  - `J_PANEL1`, `J_LED1`
- `J_ESP_L1,J_ESP_R1` remain included and show nonzero quantity/source: `C319202`, quantity `10`, source `10 JLCPCB`.
- Estimated component total shown in the export: `$35.6629` for 5 assembled boards.

The assembly-only component matches look appropriate:

- MLCCs: correct 0805 values for included capacitors.
- `C_BULK1`: radial electrolytic still included and matched.
- Schottky/TVS/ESD parts: package classes match the PCB footprints.
- `F3`: 1812 resettable PTC.
- ESP headers: 1x19 2.54mm female headers.
- LEDs: 0805 yellow/red/green indicators.
- Optocouplers: DIP-4 EL817-compatible parts.
- MOSFETs: AOD4184A TO-252.
- Resistors: correct 0805 values.
- `U1`: R-78E5.0-1.0 compatible SIP DC/DC module.

Remaining checks before approval:

- In JLC placement preview, verify polarity/orientation for:
  - all LEDs
  - all diodes
  - all TVS/ESD parts
  - all MOSFETs
  - electrolytic `C_BULK1`
- Verify `J_ESP_L1,J_ESP_R1` are vertical female socket headers with 1x19 count and 2.54mm pitch.
- Verify `U1` pinout, height, and orientation.
- Remember the hand-solder list: install `C_5V_IN1`, `F1`, `F2`, and all field terminal blocks after receiving the boards.
