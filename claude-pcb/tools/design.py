"""Single source of truth for the Rev B sauna controller board.

Defines every component, its schematic symbol, PCB footprint, placement and
pin->net mapping. Both generators (schematic + board) import this module so
the two outputs can never disagree about connectivity.

Decisions encoded here are documented in ../REV-B-DESIGN-REVIEW.md.
"""

# ---------------------------------------------------------------------------
# Net classes (matches pcb/plans/PCB-LAYOUT-PLAN.md Phase 4, carried forward)
# ---------------------------------------------------------------------------
NET_CLASSES = {
    "POWER_HV": dict(width=2.0, clearance=0.3),
    "POWER_LV": dict(width=0.5, clearance=0.2),
    "LED_OUT": dict(width=1.0, clearance=0.2),
    "SIGNAL": dict(width=0.3, clearance=0.15),
    "GND": dict(width=0.5, clearance=0.2),
}

NETS = {
    "+24V": "POWER_HV",
    "+24V_LED": "POWER_HV",
    "+24V_SAFE": "LED_OUT",     # fused safety/wetting branch, low current
    "+24V_LOGIC": "POWER_LV",
    "+5V": "POWER_LV",
    "+5V_PANEL": "POWER_LV",
    "+3V3": "SIGNAL",  # <50mA: pullups + sensors; 0.3mm everywhere
    "GND": "GND",
    "SRL250_RTN": "LED_OUT",    # post-high-limit node == COIL+
    "COIL-": "LED_OUT",
    "LED_R-": "LED_OUT",
    "LED_G-": "LED_OUT",
    "LED_B-": "LED_OUT",
    "LED_W-": "LED_OUT",
    "AUX_IN": "SIGNAL",
    "AUX_LED": "SIGNAL",
    "HL_LED": "SIGNAL",
    "SPARE_IN": "SIGNAL",
    "SPARE_LED": "SIGNAL",
    "GPIO13": "SIGNAL",
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
    "GPIO14": "SIGNAL",
    "GPIO4": "SIGNAL",
    "G_COIL": "SIGNAL",
    "G_R": "SIGNAL",
    "G_G": "SIGNAL",
    "G_B": "SIGNAL",
    "G_W": "SIGNAL",
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
# Top edge (DIN/contactor side), terminal pin row at y=6, wires exit top.
add("J_COIL", "CONN2", "MKDS_2", "COIL", (14, 6, 0),
    {1: "SRL250_RTN", 2: "COIL-"}, (118, 40),
    MPN="Phoenix MKDS 1,5/2-5,08")
add("J_AUX", "CONN2", "MKDS_2", "AUX_FB", (30, 6, 0),
    {1: "+24V_SAFE", 2: "AUX_IN"}, (118, 70),
    MPN="Phoenix MKDS 1,5/2-5,08")
add("J_LED", "CONN5", "MKDS_5", "LED_RGBW", (50, 6, 0),
    {1: "LED_R-", 2: "LED_G-", 3: "LED_B-", 4: "LED_W-", 5: "+24V_LED"},
    (200, 40), MPN="Phoenix MKDS 1,5/5-5,08")
add("J_PWR", "CONN2", "MKDS_2", "24V_IN", (112, 6, 0),
    {1: "+24V", 2: "GND"}, (30, 40),
    MPN="Phoenix MKDS 1,5/2-5,08")
# Bottom edge (sauna-harness side), pin row at y=79, wires exit bottom.
add("J_PANEL", "CONN4", "MKDS_4", "PANEL", (18, 79, 0),
    {1: "+5V_PANEL", 2: "GND", 3: "PANEL_TX", 4: "PANEL_RX"}, (262, 40),
    MPN="Phoenix MKDS 1,5/4-5,08")
add("J_SRL250", "CONN2", "MKDS_2", "SRL250", (46, 79, 0),
    {1: "+24V_SAFE", 2: "SRL250_RTN"}, (118, 55),
    MPN="Phoenix MKDS 1,5/2-5,08")
add("J_DOOR", "CONN2", "MKDS_2", "DOOR", (61, 79, 0),
    {1: "DOOR_IN", 2: "GND"}, (262, 70),
    MPN="Phoenix MKDS 1,5/2-5,08")
add("J_BENCH", "CONN3", "MKDS_3", "BENCH_T", (77, 79, 0),
    {1: "+3V3", 2: "BENCH_DATA", 3: "GND"}, (262, 100),
    MPN="Phoenix MKDS 1,5/3-5,08")
add("J_CEILING", "CONN3", "MKDS_3", "CEIL_T", (102, 79, 0),
    {1: "+3V3", 2: "CEIL_DATA", 3: "GND"}, (262, 130),
    MPN="Phoenix MKDS 1,5/3-5,08")
# Spare opto field input: 2.54 mm header, mid-board (optionally populated).
add("J_SPARE", "CONN2", "HDR_1x2", "SPARE_IN", (96, 52, 0),
    {1: "+24V_SAFE", 2: "SPARE_IN"}, (118, 85))

# --- Fuses: vertical bank on the right, fed straight from J_PWR -------------
# (Keystone 3517-style 5x20 top-access holders; VERIFY with 1:1 print)
add("F1", "FUSE", "FUSE_5x20", "5A T (LED)", (106, 14, 270),
    {1: "+24V", 2: "+24V_LED"}, (55, 40), MPN="Keystone 3517 + 5x20 5A T")
add("F2", "FUSE", "FUSE_5x20", "1A F (COIL)", (114.5, 14, 270),
    {1: "+24V", 2: "+24V_SAFE"}, (55, 55), MPN="Keystone 3517 + 5x20 1A F")
add("F3", "FUSE", "FUSE_5x20", "1A F (LOGIC)", (123, 14, 270),
    {1: "+24V", 2: "+24V_LOGIC"}, (55, 70), MPN="Keystone 3517 + 5x20 1A F")
add("PF1", "POLYFUSE", "R_1812", "750mA PTC", (11.5, 75.3, 180),
    {1: "+5V", 2: "+5V_PANEL"}, (230, 40), MPN="MF-MSMF075/24X")

# --- Power input + conversion ------------------------------------------------
add("D1", "TVS", "D_SMB", "SMBJ33A", (98, 8.5, 90),
    {1: "GND", 2: "+24V"}, (14, 100), MPN="SMBJ33A")
add("C5", "C", "C_0805", "100nF", (94, 9, 90),
    {1: "+24V", 2: "GND"}, (30, 100))
add("C4", "CP", "CP_D8_P3.5", "220uF 50V", (87, 10, 0),
    {1: "+24V", 2: "GND"}, (22, 100))
add("U1", "REG3", "SIP3_REG", "OKI-78SR-5/1.5-W36-C", (88, 33, 0),
    {1: "+24V_LOGIC", 2: "GND", 3: "+5V"}, (55, 90),
    MPN="Murata OKI-78SR-5/1.5-W36-C")
add("C1", "C", "C_1210", "10uF 50V", (99.5, 33, 90),
    {1: "+24V_LOGIC", 2: "GND"}, (40, 100))
add("C2", "C", "C_1210", "22uF 25V", (83, 38.5, 90),
    {1: "+5V", 2: "GND"}, (70, 100))
add("C3", "C", "C_0805", "100nF", (86.5, 38.5, 90),
    {1: "+5V", 2: "GND"}, (78, 100))
add("C6", "CP", "CP_D8_P3.5", "220uF 50V", (79, 16, 270),
    {1: "+24V_LED", 2: "GND"}, (208, 100))
add("C7", "C", "C_0805", "100nF", (84.5, 16, 90),
    {1: "+24V_LED", 2: "GND"}, (216, 100))
add("C8", "C", "C_0805", "100nF", (33, 66, 90),
    {1: "+3V3", 2: "GND"}, (86, 100))
add("C10", "C", "C_0805", "100nF", (4, 74.8, 90),
    {1: "+5V_PANEL", 2: "GND"}, (240, 100))

# --- Coil switch + flyback (top-left, beside J_COIL) -------------------------
add("D5", "D", "D_SMA", "SS54", (16, 14, 0),
    {1: "SRL250_RTN", 2: "COIL-"}, (100, 152), MPN="SS54")
add("Q1", "NMOS", "TO252", "AOD4184A", (19, 25, 0),
    {1: "G_COIL", 2: "COIL-", 3: "GND"}, (90, 160), MPN="AOD4184A")
add("R7", "R", "R_0805", "100R", (16.72, 33.2, 90),
    {1: "GPIO13", 2: "G_COIL"}, (84, 150))
add("R12", "R", "R_0805", "10K", (22.5, 33.2, 90),
    {1: "G_COIL", 2: "GND"}, (96, 150))

# --- LED MOSFETs: staggered 2-row bank aligned under J_LED pins --------------
# NOTE: Rev B remaps LED PWM GPIOs (R=19, G=18, B=17, W=16) so the four
# gate traces run crossing-free from the ESP header to the gate resistors.
# One-line firmware change; see REV-B-DESIGN-REVIEW.md.
add("Q2", "NMOS", "TO252", "AOD4184A", (50, 22, 0),
    {1: "G_R", 2: "LED_R-", 3: "GND"}, (150, 160), MPN="AOD4184A")
add("Q3", "NMOS", "TO252", "AOD4184A", (55.08, 34.2, 0),
    {1: "G_G", 2: "LED_G-", 3: "GND"}, (170, 160), MPN="AOD4184A")
add("Q4", "NMOS", "TO252", "AOD4184A", (60.16, 22, 0),
    {1: "G_B", 2: "LED_B-", 3: "GND"}, (190, 160), MPN="AOD4184A")
add("Q5", "NMOS", "TO252", "AOD4184A", (65.24, 34.2, 0),
    {1: "G_W", 2: "LED_W-", 3: "GND"}, (210, 160), MPN="AOD4184A")
add("R8", "R", "R_0805", "100R", (47.72, 31, 90),
    {1: "GPIO19", 2: "G_R"}, (144, 150))
add("R9", "R", "R_0805", "100R", (48, 40.6, 90),
    {1: "GPIO18", 2: "G_G"}, (164, 150))
add("R10", "R", "R_0805", "100R", (60.2, 31, 90),
    {1: "GPIO17", 2: "G_B"}, (184, 150))
add("R11", "R", "R_0805", "100R", (70.5, 36, 90),
    {1: "GPIO16", 2: "G_W"}, (204, 150))
add("R13", "R", "R_0805", "10K", (45, 25, 90),
    {1: "G_R", 2: "GND"}, (156, 150))
add("R14", "R", "R_0805", "10K", (50.5, 38.5, 90),
    {1: "G_G", 2: "GND"}, (176, 150))
add("R15", "R", "R_0805", "10K", (66, 25, 90),
    {1: "G_B", 2: "GND"}, (196, 150))
add("R16", "R", "R_0805", "10K", (70.5, 40.5, 90),
    {1: "G_W", 2: "GND"}, (216, 150))

# --- Opto-isolated 24 V inputs (LTV-817: 1=A 2=K 3=E 4=C) -------------------
# Input conditioning for AUX hangs below J_AUX; optos sit between the ESP
# socket rows with collectors facing the GPIO row.
add("R1", "R", "R_1206", "3K3 1W", (35.08, 14, 270),
    {1: "AUX_IN", 2: "AUX_LED"}, (126, 76))
add("D2", "TVS", "D_SMB", "SMBJ30CA", (39.5, 15, 90),
    {1: "GND", 2: "AUX_IN"}, (126, 90), MPN="SMBJ30CA")
add("D9", "D", "D_SOD323", "1N4148WS", (37.5, 52, 90),
    {1: "AUX_LED", 2: "GND"}, (132, 90))
add("OPT1", "OPTO", "DIP4", "LTV-817", (43, 52, 180),
    {1: "AUX_LED", 2: "GND", 3: "GND", 4: "GPIO32"}, (150, 80),
    MPN="LTV-817")
add("R4", "R", "R_0805", "10K", (42, 64, 90),
    {1: "+3V3", 2: "GPIO32"}, (162, 70))
# High-limit channel: senses 24 V presence on SRL250_RTN (post-high-limit)
add("R2", "R", "R_1206", "3K3 1W", (39.8, 48, 0),
    {1: "SRL250_RTN", 2: "HL_LED"}, (126, 110))
add("D3", "TVS", "D_SMB", "SMBJ30CA", (31.5, 49.5, 90),
    {1: "GND", 2: "SRL250_RTN"}, (126, 124), MPN="SMBJ30CA")
add("D10", "D", "D_SOD323", "1N4148WS", (35.3, 48, 0),
    {1: "HL_LED", 2: "GND"}, (132, 124))
add("OPT2", "OPTO", "DIP4", "LTV-817", (53, 52, 180),
    {1: "HL_LED", 2: "GND", 3: "GND", 4: "GPIO33"}, (150, 110),
    MPN="LTV-817")
add("R5", "R", "R_0805", "10K", (49, 64, 90),
    {1: "+3V3", 2: "GPIO33"}, (162, 100))
# Spare channel (GPIO25, matches commented-out firmware block)
add("R3", "R", "R_1206", "3K3 1W", (88, 52, 90),
    {1: "SPARE_IN", 2: "SPARE_LED"}, (126, 140))
add("D4", "TVS", "D_SMB", "SMBJ30CA", (92, 52, 90),
    {1: "GND", 2: "SPARE_IN"}, (126, 154), MPN="SMBJ30CA")
add("D11", "D", "D_SOD323", "1N4148WS", (84, 52, 90),
    {1: "SPARE_LED", 2: "GND"}, (132, 154))
add("OPT3", "OPTO", "DIP4", "LTV-817", (63, 52, 180),
    {1: "SPARE_LED", 2: "GND", 3: "GND", 4: "GPIO25"}, (150, 140),
    MPN="LTV-817")
add("R6", "R", "R_0805", "10K", (56, 64, 90),
    {1: "+3V3", 2: "GPIO25"}, (162, 130))

# --- Door input (bottom band between ESP row and connectors) -----------------
add("D6", "ESD", "D_SOD923", "ESD9B5.0", (59, 73, 0),
    {1: "DOOR_IN", 2: "GND"}, (276, 80), MPN="ESD9B5.0ST5G")
add("R18", "R", "R_0805", "1K", (63, 73, 0),
    {1: "DOOR_IN", 2: "GPIO22"}, (282, 76))
add("C9", "C", "C_0805", "100nF", (67.5, 73, 0),
    {1: "GPIO22", 2: "GND"}, (288, 86))
add("R17", "R", "R_0805", "10K", (71.5, 73, 0),
    {1: "+3V3", 2: "GPIO22"}, (294, 70))

# --- DS18B20 1-Wire ----------------------------------------------------------
add("R19", "R", "R_0805", "4K7", (78, 73, 0),
    {1: "+3V3", 2: "BENCH_DATA"}, (276, 106))
add("R21", "R", "R_0805", "100R", (82.5, 73, 0),
    {1: "BENCH_DATA", 2: "GPIO26"}, (282, 110))
add("D7", "ESD", "D_SOD923", "ESD9B5.0", (87, 73, 0),
    {1: "BENCH_DATA", 2: "GND"}, (288, 116), MPN="ESD9B5.0ST5G")
add("R20", "R", "R_0805", "4K7", (99, 73, 0),
    {1: "+3V3", 2: "CEIL_DATA"}, (276, 136))
add("R22", "R", "R_0805", "100R", (103.5, 73, 0),
    {1: "CEIL_DATA", 2: "GPIO27"}, (282, 140))
add("D8", "ESD", "D_SOD923", "ESD9B5.0", (108, 73, 0),
    {1: "CEIL_DATA", 2: "GND"}, (288, 146), MPN="ESD9B5.0ST5G")

# --- Panel UART --------------------------------------------------------------
add("U2", "USBLC6", "SOT23_6", "USBLC6-2SC6", (40.7, 74.5, 0),
    {1: "PANEL_TX", 2: "GND", 3: "PANEL_RX",
     4: "PANEL_RX", 5: "+3V3", 6: "PANEL_TX"}, (240, 70),
    MPN="USBLC6-2SC6")
add("R23", "R", "R_0805", "100R", (55, 72.6, 0),
    {1: "GPIO14", 2: "PANEL_TX"}, (228, 60))
add("R24", "R", "R_0805", "100R", (60.48, 47.5, 90),
    {1: "PANEL_RX", 2: "GPIO4"}, (228, 66))

# --- Indicators --------------------------------------------------------------
add("R25", "R", "R_0805", "10K", (98, 44, 0),
    {1: "+24V_LOGIC", 2: "LED24_A"}, (22, 130))
add("LED1", "LED", "LED_0805", "GREEN 24V", (103, 44, 0),
    {1: "LED24_A", 2: "GND"}, (22, 140))
add("R26", "R", "R_0805", "1K", (98, 47.5, 0),
    {1: "+5V", 2: "LED5_A"}, (40, 130))
add("LED2", "LED", "LED_0805", "GREEN 5V", (103, 47.5, 0),
    {1: "LED5_A", 2: "GND"}, (40, 140))
add("R27", "R", "R_0805", "1K", (33, 57, 90),
    {1: "GPIO23", 2: "FAULT_A"}, (58, 130))
add("LED3", "LED", "LED_0805", "RED FAULT", (33, 61.5, 90),
    {1: "FAULT_A", 2: "GND"}, (58, 140))

# --- ESP32 DevKitC v4 socket (2x 1x19 female, 25.4 mm row spacing) ----------
# Antenna points LEFT (-x). Row A (y=44) = DevKitC "GND/GPIO23" column,
# Row B (y=69.4) = DevKitC "3V3" column. Pin 1 of both rows at antenna end.
ESP2_PINS = {1: "GND", 2: "GPIO23", 3: "GPIO22", 4: None, 5: None, 6: None,
             7: "GND", 8: "GPIO19", 9: "GPIO18", 10: None, 11: "GPIO17",
             12: "GPIO16", 13: "GPIO4", 14: None, 15: None, 16: None,
             17: None, 18: None, 19: None}
ESP1_PINS = {1: "+3V3", 2: None, 3: None, 4: None, 5: None, 6: None,
             7: "GPIO32", 8: "GPIO33", 9: "GPIO25", 10: "GPIO26",
             11: "GPIO27", 12: "GPIO14", 13: None, 14: "GND", 15: "GPIO13",
             16: None, 17: None, 18: None, 19: "+5V"}
add("J_ESP2", "CONN19", "SOCKET_1x19", "ESP_ROW_GND23", (30, 44, 0),
    ESP2_PINS, (330, 40), MPN="PinSocket 1x19 2.54mm")
add("J_ESP1", "CONN19", "SOCKET_1x19", "ESP_ROW_3V3", (30, 69.4, 0),
    ESP1_PINS, (380, 40), MPN="PinSocket 1x19 2.54mm")

# --- Test points -------------------------------------------------------------
_tps = [("TP1", "+24V", (102, 8.5)), ("TP2", "+5V", (80, 38.5)),
        ("TP3", "+3V3", (36.5, 66)), ("TP4", "GND", (98, 13)),
        ("TP5", "LED_R-", (50, 12.5)), ("TP6", "LED_G-", (55.08, 12.5)),
        ("TP7", "LED_B-", (60.16, 12.5)), ("TP8", "LED_W-", (65.24, 12.5)),
        ("TP9", "COIL-", (19.08, 17.5)), ("TP10", "GPIO32", (45.24, 65.5)),
        ("TP11", "GPIO33", (46, 61)), ("TP12", "GPIO22", (63, 66)),
        ("TP13", "PANEL_TX", (39.5, 78)), ("TP14", "PANEL_RX", (41.9, 78)),
        ("TP15", "AUX_LED", (37.5, 55.5))]
for i, (ref, net, at) in enumerate(_tps):
    add(ref, "TP", "TESTPOINT", net, (at[0], at[1], 0), {1: net},
        (415 + 0 * i, 40 + 8 * i))

# ---------------------------------------------------------------------------
# Board mechanicals
# ---------------------------------------------------------------------------
BOARD = dict(
    width=130.0, height=85.0, corner_radius=5.0,
    mounting_holes=[(5, 5), (125, 5), (5, 80), (125, 80)],  # M3, non-plated
    # Antenna keepout: no copper / no parts. Module antenna end ~x=24.
    antenna_keepout=(0.0, 38.0, 28.0, 73.0),  # x1, y1, x2, y2
)

TITLE = "Alex's Super Sauna Commander"
REV = "B"
