"""Single source of truth for the Rev B sauna control board.

Defines every component, its schematic symbol, PCB footprint, placement and
pin->net mapping. Both generators (schematic + board) import this module so
the two outputs can never disagree about connectivity.

The high-level rationale is summarized in ../../../docs/DESIGN.md and the board
workflow is documented in ../README.md.
"""

# ---------------------------------------------------------------------------
# Net classes.
# ---------------------------------------------------------------------------
NET_CLASSES = {
    "POWER_HV": dict(width=2.0, clearance=0.3),
    "POWER_LV": dict(width=0.5, clearance=0.2),
    "LED_OUT": dict(width=1.0, clearance=0.2),
    "SIGNAL": dict(width=0.2, clearance=0.15),
    "GND": dict(width=0.3, clearance=0.2),
}

NETS = {
    "+24V": "POWER_HV",
    "+24V_LED": "POWER_HV",
    "+24V_AUX": "LED_OUT",
    "+24V_SAFE": "LED_OUT",     # fused safety/wetting branch, low current
    "+24V_LOGIC": "POWER_LV",
    "+5V": "POWER_LV",
    "+5V_PANEL": "POWER_LV",
    "+3V3": "SIGNAL",  # <50mA: pullups + sensors; 0.3mm everywhere
    "GND": "GND",
    "SRL250_RTN": "LED_OUT",    # post-high-limit node == COIL+
    "COIL-": "LED_OUT",
    "AUX_OUT-": "LED_OUT",
    "LED_R-": "LED_OUT",
    "LED_G-": "LED_OUT",
    "LED_B-": "LED_OUT",
    "LED_W-": "LED_OUT",
    "RELAY_FB_IN": "SIGNAL",
    "RELAY_FB_LED": "SIGNAL",
    "HL_LED": "SIGNAL",
    "GPIO16": "SIGNAL",
    "GPIO17": "SIGNAL",
    "GPIO18": "SIGNAL",
    "GPIO19": "SIGNAL",
    "GPIO22": "SIGNAL",
    "GPIO23": "SIGNAL",
    "GPIO25": "SIGNAL",
    "GPIO26": "SIGNAL",
    "GPIO27": "SIGNAL",
    "GPIO32": "SIGNAL",
    "GPIO33": "SIGNAL",
    "GPIO34": "SIGNAL",
    "GPIO35": "SIGNAL",
    "GPIO4": "SIGNAL",
    "G_COIL": "SIGNAL",
    "G_AUX": "SIGNAL",
    "G_R": "SIGNAL",
    "G_G": "SIGNAL",
    "G_B": "SIGNAL",
    "G_W": "SIGNAL",
    "ACT_R": "SIGNAL",   # RGBW activity-indicator LED anodes (gate-sensed)
    "ACT_G": "SIGNAL",
    "ACT_B": "SIGNAL",
    "ACT_W": "SIGNAL",
    "DOOR_IN": "SIGNAL",
    "BENCH_DATA": "SIGNAL",
    "CEIL_DATA": "SIGNAL",
    "PANEL_TX": "SIGNAL",
    "PANEL_RX": "SIGNAL",
    "FAULT_A": "SIGNAL",
    "LED24_A": "SIGNAL",
    "LED5_A": "SIGNAL",
}

# ---------------------------------------------------------------------------
# Components.
# Each entry: ref -> dict(
#   symbol   : schematic symbol key (see generate_schematic.SYMBOLS)
#   footprint: footprint key (see footprints.FOOTPRINTS)
#   value    : value string
#   at       : (x, y, rot) board placement, mm / degrees (KiCad: +y is down)
#   nets     : {pin_number(str): net name or None for NC}
#   sch      : (x, y) schematic sheet position, mm
#   fields   : optional extra schematic fields (e.g. MPN)
# )
# ---------------------------------------------------------------------------

C = {}


def add(ref, symbol, footprint, value, at, nets, sch, **fields):
    C[ref] = dict(symbol=symbol, footprint=footprint, value=value, at=at,
                  nets={str(k): v for k, v in nets.items()}, sch=sch,
                  fields=fields)


# --- Field connectors -------------------------------------------------------
# Floor plan (contactor sits to the RIGHT of this board):
#   RIGHT edge  : J_COIL, J_RELAY_FB  (land right next to the contactor)
#   BOTTOM edge : J_PANEL, J_DOOR, J_BENCH, J_CEILING, J_SRL250 (sauna room;
#                 SRL250 on the right side, toward the coil/contactor corner)
#   TOP edge    : J_PWR (24 V supply feed)
#   LEFT edge   : J_LED (upper-left, above the antenna keepout)
# Terminal blocks now use vertical-entry WJ2EDGV parts. Placement can sit closer
# to the board edge than the earlier edge-entry layout, but keep enough room
# for labels, screwdriver access, and field wiring service clearance.

# Right edge (rot 90 -> pin row vertical, wires exit +x toward contactor).
add("J_COIL", "CONN2", "MKDS_2", "COIL", (117.156, 43.72, 90),
    {1: "SRL250_RTN", 2: "COIL-"}, (118, 40),
    MPN="Phoenix MKDS 1,5/2-5,08")
add("J_RELAY_FB", "CONN2", "MKDS_2", "RELAY_FB", (117.156, 64.1, 90),
    {1: "+24V_SAFE", 2: "RELAY_FB_IN"}, (118, 70),
    MPN="Phoenix MKDS 1,5/2-5,08")
# Left edge upper (rot 270 -> pin row vertical, wires exit -x). Above keepout.
add("J_LED", "CONN5", "MKDS_5", "LED_RGBW", (7.698, 17.05, -90),
    {1: "LED_R-", 2: "LED_G-", 3: "LED_B-", 4: "LED_W-", 5: "+24V_LED"},
    (200, 40), MPN="Phoenix MKDS 1,5/5-5,08")
# Top edge: 24 V supply feed.
add("J_PWR", "CONN2", "MKDS_2", "24V_IN", (64.34, 10.446, 180),
    {1: "+24V", 2: "GND"}, (30, 40),
    MPN="Phoenix MKDS 1,5/2-5,08")
# Bottom edge (sauna-harness side). SRL250 on the right side of the row.
add("J_PANEL", "CONN4", "MKDS_4", "PANEL", (14.78, 87.408, 0),
    {1: "+5V_PANEL", 2: "GND", 3: "PANEL_TX", 4: "PANEL_RX"}, (262, 40),
    MPN="Phoenix MKDS 1,5/4-5,08")
add("J_DOOR", "CONN2", "MKDS_2", "DOOR", (40.81, 87.408, 0),
    {1: "DOOR_IN", 2: "GND"}, (262, 70),
    MPN="Phoenix MKDS 1,5/2-5,08")
add("J_BENCH", "CONN3", "MKDS_3", "BENCH_T", (57.99, 87.408, 0),
    {1: "+3V3", 2: "BENCH_DATA", 3: "GND"}, (262, 100),
    MPN="Phoenix MKDS 1,5/3-5,08")
add("J_CEILING", "CONN3", "MKDS_3", "CEIL_T", (79.55, 87.408, 0),
    {1: "+3V3", 2: "CEIL_DATA", 3: "GND"}, (262, 130),
    MPN="Phoenix MKDS 1,5/3-5,08")
add("J_SRL250", "CONN2", "MKDS_2", "SRL250", (102.44, 87.408, 0),
    {1: "+24V_SAFE", 2: "SRL250_RTN"}, (118, 55),
    MPN="Phoenix MKDS 1,5/2-5,08")
# Spare opto field input: 2.54 mm header, right-center (optionally populated).

# --- Resettable branch protection ------------------------------------------
add("F1", "POLYFUSE", "PTC_2920", "3A PTC (LED)", (76.024, 14.062, -90),
    {1: "+24V", 2: "+24V_LED"}, (55, 40),
    MPN="JLC C719172")
add("F2", "POLYFUSE", "PTC_1812", "750mA PTC (COIL)", (76.024, 25.94, -90),
    {1: "+24V", 2: "+24V_SAFE"}, (55, 55),
    MPN="Bourns MF-MSMF075/24-2 or equivalent")
add("F3", "POLYFUSE", "PTC_1812", "750mA PTC (LOGIC)", (86.692, 25.94, -90),
    {1: "+24V", 2: "+24V_LOGIC"}, (55, 70),
    MPN="Bourns MF-MSMF075/24-2 or equivalent")
add("PF1", "POLYFUSE", "R_1812", "750mA PTC", (16.42, 74.54, 180),
    {1: "+5V", 2: "+5V_PANEL"}, (230, 40), MPN="MF-MSMF075/24X")

# --- Optional AUX 24 V low-side output scaffold ----------------------------
# This output is intentionally placed off the right side of the board for now.
# Drag/place/route it in KiCad once the final Rev B floorplan has room. GPIO4
# is ESP32 DevKitC row GND/GPIO23 pin 13.
add("F4", "POLYFUSE", "PTC_2920", "2A PTC (AUX)", (86.692, 14.122, -90),
    {1: "+24V", 2: "+24V_AUX"}, (55, 85),
    MPN="JLC C139284")
add("J_AUX_OUT", "CONN2", "MKDS_2", "AUX_OUT", (101.17, 10.446, 180),
    {1: "+24V_AUX", 2: "AUX_OUT-"}, (118, 88),
    MPN="Phoenix MKDS 1,5/2-5,08")
add("D11", "D", "D_SMA", "SS54", (102.218, 23.146, 180),
    {1: "+24V_AUX", 2: "AUX_OUT-"}, (126, 182), MPN="SS54")
add("Q6", "NMOS", "TO252", "AOD4184A", (100.092, 28.988, -90),
    {1: "G_AUX", 2: "AUX_OUT-", 3: "GND"}, (116, 190), MPN="AOD4184A")
add("R32", "R", "R_0805", "100R", (92.28, 28.8, 90),
    {1: "GPIO4", 2: "G_AUX"}, (108, 180))
add("R33", "R", "R_0805", "10K", (95.394, 23.654, 0),
    {1: "G_AUX", 2: "GND"}, (120, 180))

# --- Power input + conversion (top-center, by J_PWR) ------------------------
add("D1", "TVS", "D_SMB", "SMBJ33A", (56.72, 27.55, 90),
    {1: "GND", 2: "+24V"}, (14, 100), MPN="SMBJ33A")
add("C5", "C", "C_0805", "100nF", (56.278, 22.13, 180),
    {1: "+24V", 2: "GND"}, (30, 100))
add("C4", "CP", "CP_D8_P3.5", "220uF 50V", (62.11, 26.02, 0),
    {1: "+24V", 2: "GND"}, (22, 100))
add("U1", "REG3", "SIP3_REG", "K7805-2000R3", (88.724, 40.418, 180),
    {1: "+24V_LOGIC", 2: "GND", 3: "+5V"}, (55, 90),
    MPN="K7805-2000R3")  # 5V/2A non-isolated buck, LM78xx-pin SIP-3 (JLC ~$1-2)
add("C1", "C", "C_1210", "10uF 50V", (95, 40, 90),
    {1: "+24V_LOGIC", 2: "GND"}, (40, 100))
add("C2", "C", "C_1210", "22uF 25V", (84.508, 46.5, 90),
    {1: "+5V", 2: "GND"}, (70, 100))
add("C3", "C", "C_0805", "100nF", (87.708, 47.088, 90),
    {1: "+5V", 2: "GND"}, (78, 100))
# LED bulk + decoupling, near J_LED (left).
add("C6", "CP", "CP_D8_P3.5", "220uF 50V", (57.99, 37.116, 0),
    {1: "+24V_LED", 2: "GND"}, (208, 100))
add("C7", "C", "C_0805", "100nF", (66.702, 35.45, -90),
    {1: "+24V_LED", 2: "GND"}, (216, 100))
# Logic decoupling under the ESP module (between header rows, low profile).
add("C8", "C", "C_0805", "100nF", (36.4, 74.52, -90),
    {1: "+3V3", 2: "GND"}, (86, 100))
add("C10", "C", "C_0805", "100nF", (11.0, 74.54, -90),
    {1: "+5V_PANEL", 2: "GND"}, (240, 100))

# --- Coil switch + flyback (right-center, beside J_COIL) ---------------------
add("D5", "D", "D_SMA", "SS54", (118.45, 32.26, 180),
    {1: "SRL250_RTN", 2: "COIL-"}, (100, 152), MPN="SS54")
add("Q1", "NMOS", "TO252", "AOD4184A", (114.91, 25.91, 270),
    {1: "G_COIL", 2: "COIL-", 3: "GND"}, (90, 160), MPN="AOD4184A")
add("R7", "R", "R_0805", "100R", (104.538, 43.466, 0),
    {1: "GPIO23", 2: "G_COIL"}, (84, 150))
add("R12", "R", "R_0805", "10K", (104.538, 39.148, 180),
    {1: "G_COIL", 2: "GND"}, (96, 150))

# --- LED MOSFETs: row in upper-left, drains exit left to J_LED ---------------
# NOTE: Rev B remaps LED PWM GPIOs (R=19, G=18, B=17, W=16) so the four
# gate traces run crossing-free from the ESP header to the gate resistors.
# One-line firmware change; see docs/FIRMWARE.md.
add("Q2", "NMOS", "TO252", "AOD4184A", (22, 18, 0),
    {1: "G_R", 2: "LED_R-", 3: "GND"}, (150, 160), MPN="AOD4184A")
add("Q3", "NMOS", "TO252", "AOD4184A", (31, 18, 0),
    {1: "G_G", 2: "LED_G-", 3: "GND"}, (170, 160), MPN="AOD4184A")
add("Q4", "NMOS", "TO252", "AOD4184A", (40, 18, 0),
    {1: "G_B", 2: "LED_B-", 3: "GND"}, (190, 160), MPN="AOD4184A")
add("Q5", "NMOS", "TO252", "AOD4184A", (49, 18, 0),
    {1: "G_W", 2: "LED_W-", 3: "GND"}, (210, 160), MPN="AOD4184A")
add("R8", "R", "R_0805", "100R", (23.7, 26.5, 90),
    {1: "GPIO19", 2: "G_R"}, (144, 150))
add("R9", "R", "R_0805", "100R", (32.59, 26.5, 90),
    {1: "GPIO18", 2: "G_G"}, (164, 150))
add("R10", "R", "R_0805", "100R", (41.59, 26.5, 90),
    {1: "GPIO17", 2: "G_B"}, (184, 150))
add("R11", "R", "R_0805", "100R", (50.59, 26.5, 90),
    {1: "GPIO16", 2: "G_W"}, (204, 150))
add("R13", "R", "R_0805", "10K", (23.7, 30.5, 90),
    {1: "G_R", 2: "GND"}, (156, 150))
add("R14", "R", "R_0805", "10K", (32.59, 30.5, 90),
    {1: "G_G", 2: "GND"}, (176, 150))
add("R15", "R", "R_0805", "10K", (41.59, 30.5, 90),
    {1: "G_B", 2: "GND"}, (196, 150))
add("R16", "R", "R_0805", "10K", (50.59, 30.5, 90),
    {1: "G_W", 2: "GND"}, (216, 150))

# --- RGBW activity indicators (gate-sensed) ---------------------------------
# A red LED per channel lights when the ESP drives that gate; PWM duty -> visible
# brightness, so you see each channel is active and how hard. Each is the gate
# node through 1K (same ~1.3mA / 3.3V as the FAULT LED): G_x -[R]- ACT_x -[LED]-
# GND. Placed + hand-routed in KiCad: LED (y26.5) over series R (y30.5) in the
# left half of each channel column, beside the gate resistor/pulldown pair.
# Pairs: R28/LED4=R, R29/LED5=G, R30/LED6=B, R31/LED7=W.
add("R28", "R", "R_0805", "1K", (19.89, 30.5, 90),
    {1: "G_R", 2: "ACT_R"}, (148, 180))
add("LED4", "LED", "LED_0805", "RED ACT", (19.89, 26.5, 90),
    {1: "ACT_R", 2: "GND"}, (158, 180), MPN="red 0805")
add("R29", "R", "R_0805", "1K", (28.78, 30.5, 90),
    {1: "G_G", 2: "ACT_G"}, (168, 180))
add("LED5", "LED", "LED_0805", "RED ACT", (28.78, 26.5, 90),
    {1: "ACT_G", 2: "GND"}, (178, 180), MPN="red 0805")
add("R30", "R", "R_0805", "1K", (37.67, 30.5, 90),
    {1: "G_B", 2: "ACT_B"}, (188, 180))
add("LED6", "LED", "LED_0805", "RED ACT", (37.67, 26.5, 90),
    {1: "ACT_B", 2: "GND"}, (198, 180), MPN="red 0805")
add("R31", "R", "R_0805", "1K", (46.56, 30.5, 90),
    {1: "G_W", 2: "ACT_W"}, (208, 180))
add("LED7", "LED", "LED_0805", "RED ACT", (46.56, 26.5, 90),
    {1: "ACT_W", 2: "GND"}, (218, 180), MPN="red 0805")

# --- Opto-isolated 24 V inputs (LTV-817: 1=A 2=K 3=E 4=C) -------------------
# Both optos cluster right-center, near J_RELAY_FB / J_SRL250.
# Relay feedback channel (input from J_RELAY_FB).
add("R1", "R", "R_1206", "3K3", (96.09, 54.06, 90),
    {1: "RELAY_FB_IN", 2: "RELAY_FB_LED"}, (126, 76))
add("D2", "TVS", "D_SMB", "SMBJ30CA", (115.48, 51.34, 180),
    {1: "GND", 2: "RELAY_FB_IN"}, (126, 90), MPN="SMBJ30CA")
add("D9", "D", "D_SOD323", "1N4148WS", (92.28, 57.69, 0),
    {1: "RELAY_FB_LED", 2: "GND"}, (132, 90))
add("OPT_RELAY_FB", "OPTO", "SOP4_OPTO", "LTV-817S", (91.255, 55.13, 90),
    {1: "RELAY_FB_LED", 2: "GND", 3: "GND", 4: "GPIO34"}, (150, 80),
    MPN="LTV-817S")
add("R4", "R", "R_0805", "10K", (82.12, 57.37, 90),
    {1: "+3V3", 2: "GPIO34"}, (162, 70))
# High-limit channel: senses 24 V presence on SRL250_RTN (post-high-limit).
add("R2", "R", "R_1206", "3K3", (118.95, 71.66, 180),
    {1: "SRL250_RTN", 2: "HL_LED"}, (126, 110))
add("D3", "TVS", "D_SMB", "SMBJ30CA", (117.68, 79.28, 90),
    {1: "GND", 2: "SRL250_RTN"}, (126, 124), MPN="SMBJ30CA")
add("D10", "D", "D_SOD323", "1N4148WS", (108.79, 52.61, 0),
    {1: "HL_LED", 2: "GND"}, (132, 124))
add("OPT2", "OPTO", "SOP4_OPTO", "LTV-817S", (91.255, 65.29, 90),
    {1: "HL_LED", 2: "GND", 3: "GND", 4: "GPIO35"}, (150, 110),
    MPN="LTV-817S")
add("R5", "R", "R_0805", "10K", (82.12, 66.006, 90),
    {1: "+3V3", 2: "GPIO35"}, (162, 100))
# (Spare opto channel removed -- not needed. Its former D11 reference is now
#  reused by the optional AUX flyback diode.)

# --- Door input (bottom band, above J_DOOR) ---------------------------------
add("D6", "ESD", "D_SOD923", "ESD9B5.0", (39.22, 73.876, 180),
    {1: "DOOR_IN", 2: "GND"}, (276, 80), MPN="ESD9B5.0ST5G")
add("R18", "R", "R_0805", "1K", (42.05, 73.946, 0),
    {1: "DOOR_IN", 2: "GPIO25"}, (282, 76))
add("C9", "C", "C_0805", "100nF", (46.05, 73.946, 0),
    {1: "GPIO25", 2: "GND"}, (288, 86))
add("R17", "R", "R_0805", "10K", (50.05, 73.946, 0),
    {1: "+3V3", 2: "GPIO25"}, (294, 70))

# --- DS18B20 1-Wire (bottom band, above J_BENCH / J_CEILING) ----------------
add("R19", "R", "R_0805", "4K7", (55.45, 73.88, 90),
    {1: "+3V3", 2: "BENCH_DATA"}, (276, 106))
add("R21", "R", "R_0805", "100R", (57.99, 73.88, 90),
    {1: "BENCH_DATA", 2: "GPIO26"}, (282, 110))
add("D7", "ESD", "D_SOD923", "ESD9B5.0", (61.03, 74.2, 0),
    {1: "BENCH_DATA", 2: "GND"}, (288, 116), MPN="ESD9B5.0ST5G")
add("R20", "R", "R_0805", "4K7", (78, 73, 0),
    {1: "+3V3", 2: "CEIL_DATA"}, (276, 136))
add("R22", "R", "R_0805", "100R", (82, 73, 0),
    {1: "CEIL_DATA", 2: "GPIO27"}, (282, 140))
add("D8", "ESD", "D_SOD923", "ESD9B5.0", (86, 73, 0),
    {1: "CEIL_DATA", 2: "GND"}, (288, 146), MPN="ESD9B5.0ST5G")

# --- Panel UART (under ESP module, between header rows; low profile) ---------
add("U2", "USBLC6", "SOT23_6", "USBLC6-2SC6", (32.59, 74.52, -90),
    {1: "PANEL_TX", 2: "GND", 3: "PANEL_RX",
     4: "PANEL_RX", 5: "+3V3", 6: "PANEL_TX"}, (240, 70),
    MPN="USBLC6-2SC6")
add("R23", "R", "R_0805", "100R", (24.97, 74.52, -90),
    {1: "GPIO32", 2: "PANEL_TX"}, (228, 60))
add("R24", "R", "R_0805", "100R", (27.51, 74.52, 90),
    {1: "PANEL_RX", 2: "GPIO33"}, (228, 66))

# --- Indicators (top-right corner, above J_COIL) ----------------------------
add("R25", "R", "R_0805", "10K", (107.555, 10.828, 0),
    {1: "+24V_LOGIC", 2: "LED24_A"}, (22, 130))
add("LED1", "LED", "LED_0805", "GREEN 24V", (112.555, 10.828, 0),
    {1: "LED24_A", 2: "GND"}, (22, 140))
add("R26", "R", "R_0805", "1K", (107.555, 14.828, 0),
    {1: "+5V", 2: "LED5_A"}, (40, 130))
add("LED2", "LED", "LED_0805", "GREEN 5V", (112.555, 14.828, 0),
    {1: "LED5_A", 2: "GND"}, (40, 140))
add("R27", "R", "R_0805", "1K", (107.555, 18.828, 0),
    {1: "GPIO22", 2: "FAULT_A"}, (58, 130))
add("LED3", "LED", "LED_0805", "RED FAULT", (112.555, 18.828, 0),
    {1: "FAULT_A", 2: "GND"}, (58, 140))

# --- ESP32 DevKitC v4 socket (2x 1x19 female, 25.4 mm row spacing) ----------
# Antenna points LEFT (-x). Row A (y=44) = DevKitC "GND/GPIO23" column,
# Row B (y=69.4) = DevKitC "3V3" column. Pin 1 of both rows at antenna end.
ESP2_PINS = {1: "GND", 2: "GPIO23", 3: "GPIO22", 4: None, 5: None, 6: None,
             7: "GND", 8: "GPIO19", 9: "GPIO18", 10: None, 11: "GPIO17",
             12: "GPIO16", 13: "GPIO4", 14: None, 15: None, 16: None,
             17: None, 18: None, 19: None}
ESP1_PINS = {1: "+3V3", 2: None, 3: None, 4: None, 5: "GPIO34", 6: "GPIO35",
             7: "GPIO32", 8: "GPIO33", 9: "GPIO25", 10: "GPIO26",
             11: "GPIO27", 12: None, 13: None, 14: "GND", 15: None,
             16: None, 17: None, 18: None, 19: "+5V"}
add("J_ESP2", "CONN19", "SOCKET_1x19", "ESP_ROW_GND23", (30, 44, 0),
    ESP2_PINS, (330, 40), MPN="PinSocket 1x19 2.54mm")
add("J_ESP1", "CONN19", "SOCKET_1x19", "ESP_ROW_3V3", (30, 69.4, 0),
    ESP1_PINS, (380, 40), MPN="PinSocket 1x19 2.54mm")

# --- Test points -------------------------------------------------------------
# Only internal-node probes are kept. Test points that merely duplicated a
# terminal-block pin (GND, LED R/G/B/W-, COIL-, PANEL TX/RX) were removed --
# those nets are probed directly at their MKDS connector. Reference numbers
# are intentionally NOT renumbered so they match the board edited in KiCad.
# GPIO probes (TP10/11/12) dropped too -- those signals are reachable on the
# ESP DevKitC header pins directly. TP3 (+3V3) relocated out from under the
# ESP socket so it stays accessible with the module seated.
_tps = [("TP2", "+5V", (98.63, 71.66)),
        ("TP3", "+3V3", (94.82, 71.66))]  # TP15 (RELAY_FB_LED) removed by hand in KiCad
for i, (ref, net, at) in enumerate(_tps):
    add(ref, "TP", "TESTPOINT", net, (at[0], at[1], 0), {1: net},
        (415 + 0 * i, 40 + 8 * i))

# ---------------------------------------------------------------------------
# Board mechanicals
# ---------------------------------------------------------------------------
BOARD = dict(
    width=120.761, height=88.0, corner_radius=5.0,
    # Where the board sits on the A4 editor sheet (centered for editing ease).
    # Applied only at .kicad_pcb generation; design/route/check work at origin.
    page_origin=(82.44, 50.18),
    mounting_holes=[(5, 5), (125, 5), (5, 88), (125, 88)],  # set by TRIM below
    # Antenna keepout: no copper / no parts (sized in KiCad to the module's
    # actual antenna footprint). x1, y1, x2, y2  (pre-trim; shifted by TRIM)
    antenna_keepout=(8.968, 42.002, 28.018, 71.646),
)

# --- Board size reduction --------------------------------------------------
# The top 5 mm and left 2 mm were emptied (J_PWR/C4/J_LED moved inward), so the
# outline is trimmed there and re-origined to (0,0). Positions above are in the
# pre-trim frame; this shifts everything by -(TRIM) into the 128x88 board.
TRIM = (2.0, 5.0)
for _ref in C:
    _x, _y, _a = C[_ref]["at"]
    C[_ref]["at"] = (round(_x - TRIM[0], 3), round(_y - TRIM[1], 3), _a)
_k = BOARD["antenna_keepout"]
BOARD["antenna_keepout"] = (round(_k[0] - TRIM[0], 3), round(_k[1] - TRIM[1], 3),
                            round(_k[2] - TRIM[0], 3), round(_k[3] - TRIM[1], 3))
BOARD["mounting_holes"] = [(5, 5), (BOARD["width"] - 5, 5),
                           (5, BOARD["height"] - 5),
                           (BOARD["width"] - 5, BOARD["height"] - 5)]

TITLE = "Alex's Super Sauna Commander"
REV = "B"
