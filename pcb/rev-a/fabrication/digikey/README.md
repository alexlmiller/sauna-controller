# Digi-Key Hand-Assembly Buy List

This folder tracks the parts that are not being assembled by JLCPCB and need to be sourced separately.

Primary file:

- `sauna-controller-digikey-buy-list.csv`

Assumptions:

- Quantities are based on 5 assembled boards.
- Suggested order quantities include small spares for hand assembly.
- JLCPCB is still expected to assemble the SMD parts and ESP32 socket headers from the assembly BOM.
- The ESP32 DevKitC, external 24 V power supply, contactor, CrowPanel, and field wiring are not included here.

Open decisions before ordering the PCB:

- Terminal blocks are Phoenix MKDS screw terminals matching the current 5.08 mm footprints. WAGO lever terminals were considered but rejected due to cost and footprint mismatch.
- The current fuse footprints are for Schurter OG clip-style holders, not the Schurter OGN block holder. Each fuse uses two clips; each clip has two through-hole legs. That is why each fuse footprint has four holes but only two electrical nodes.
- `C_5V_IN1` is currently shown as 22 uF / 50 V in the design. The practical Digi-Key selection is 10 uF / 50 V in the same 1210 footprint. This is consistent with R-78E-style input filtering guidance, but the schematic/value should be updated to 10 uF / 50 V if we use it.
- F1 was originally marked 7.5A time-delay. Good Digi-Key 5x20 time-delay options are 5 A and 6.3 A. For a roughly 40 W max LED load at 24 V, either is still comfortably above normal load current; pick one and update silkscreen/assembly notes.
