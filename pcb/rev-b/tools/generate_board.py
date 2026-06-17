#!/usr/bin/env python3
"""Generate pcb/rev-b/sauna-rev-b.kicad_pcb from tools/design.py + routing.py.

Produces a complete 2-layer board: outline, non-plated mounting holes,
placed footprints with net assignments, silkscreen labels, routed traces,
vias, a solid B.Cu GND plane and the antenna keepout zone.
"""
import math
import os
import sys
import uuid as uuidlib

sys.path.insert(0, os.path.dirname(__file__))
import design  # noqa: E402
import routing  # noqa: E402
from design import C, NETS, NET_CLASSES, BOARD, TITLE, REV  # noqa: E402
from footprints import FOOTPRINTS, MOUNTING_HOLE  # noqa: E402
from generate_bom import lcsc_for  # noqa: E402  (LCSC part # per footprint+value)

from kiutils.board import Board
from kiutils.footprint import Footprint, Pad, Attributes, DrillDefinition, Model
from kiutils.items.common import Position, Net, Effects, Font, Property
from kiutils.items.fpitems import FpText, FpRect
from kiutils.items.gritems import GrText, GrLine, GrArc
from kiutils.items.brditems import Segment, Via
from kiutils.items.zones import Zone, ZonePolygon, Hatch, FillSettings, \
    KeepoutSettings
from kiutils.items.common import Coordinate

NS = uuidlib.UUID("c4a7d2b1-88e3-4f0a-b6d1-7e2f9a3c5d10")


def uid(*parts):
    return str(uuidlib.uuid5(NS, "/".join(str(p) for p in parts)))


# net name -> number (GND first after unconnected, then sorted)
NET_NUMBERS = {"": 0}
for i, name in enumerate(sorted(NETS), start=1):
    NET_NUMBERS[name] = i


def rot(px, py, angle):
    a = math.radians(angle)
    # KiCad board space: +y down; positive footprint angle = CCW on screen
    return (px * math.cos(a) + py * math.sin(a),
            -px * math.sin(a) + py * math.cos(a))


def pad_abs(comp, pad):
    """absolute board position of a pad center"""
    x, y, ang = comp["at"]
    num, ptype, shape, (px, py), size, drill = pad
    dx, dy = rot(px, py, ang)
    return (x + dx, y + dy)


def fp_effects(h=1.0, thick=0.15):
    return Effects(font=Font(height=h, width=h, thickness=thick))


# ---------------------------------------------------------------------------
# 3D models for the KiCad 3D viewer (cosmetic only -- not in Gerbers/CPL/BOM).
# Paths resolve via the built-in ${KICAD10_3DMODEL_DIR} env var. KiCad's stock
# footprints all use zero model offset, so a model's origin sits at its
# footprint origin; that lets us reuse the stock models by matching origins.
#
# Most of our footprints share KiCad's pad origin exactly -> drop in with no
# transform. A few we lay out pins-along-X where KiCad uses pins-along-Y, so
# our pads = KiCad's rotated +90 deg; those models need a Z rotation. KiCad's
# model Z-rotation is negated vs board rotation, so board +90 -> rotate Z -90
# (sign confirmed by render).
# fmt: footprint -> (rel_path, rotZ, (ox,oy,oz), optional (sx,sy,sz)).
MODEL_DIR = "${KICAD10_3DMODEL_DIR}"
R90 = -90.0
MODELS = {
    # symmetric SMD passives/diodes: pads identical to KiCad, no transform
    "R_0805":   ("Resistor_SMD.3dshapes/R_0805_2012Metric.step", 0, (0, 0, 0)),
    "C_0805":   ("Capacitor_SMD.3dshapes/C_0805_2012Metric.step", 0, (0, 0, 0)),
    "LED_0805": ("LED_SMD.3dshapes/LED_0805_2012Metric.step", 0, (0, 0, 0)),
    "R_1206":   ("Resistor_SMD.3dshapes/R_1206_3216Metric.step", 0, (0, 0, 0)),
    "C_1210":   ("Capacitor_SMD.3dshapes/C_1210_3225Metric.step", 0, (0, 0, 0)),
    "R_1812":   ("Resistor_SMD.3dshapes/R_1812_4532Metric.step", 0, (0, 0, 0)),
    # KiCad 10 ships SMD fuse models through 1210, but not 1812/2920; scale
    # the stock 1210 fuse body so PTCs render at their package size in 3D.
    "PTC_1812": ("Fuse.3dshapes/Fuse_1210_3225Metric.step", 0, (0, 0, 0),
                 (1.406, 1.28, 1.0)),
    "PTC_2920": ("Fuse.3dshapes/Fuse_1210_3225Metric.step", 0, (0, 0, 0),
                 (2.297, 2.04, 1.0)),
    "D_SMA":    ("Diode_SMD.3dshapes/D_SMA.step", 0, (0, 0, 0)),
    "D_SMB":    ("Diode_SMD.3dshapes/D_SMB.step", 0, (0, 0, 0)),
    "D_SOD323": ("Diode_SMD.3dshapes/D_SOD-323.step", 0, (0, 0, 0)),
    "D_SOD923": ("Diode_SMD.3dshapes/D_SOD-923.step", 0, (0, 0, 0)),
    # our pads = KiCad standard rotated +90
    "SOT23_6":  ("Package_TO_SOT_SMD.3dshapes/SOT-23-6.step", R90, (0, 0, 0)),
    "TO252":    ("Package_TO_SOT_SMD.3dshapes/TO-252-2.step", R90, (0, 0, 0)),
    "SOCKET_1x19": ("Connector_PinSocket_2.54mm.3dshapes/"
                    "PinSocket_1x19_P2.54mm_Vertical.step", R90, (0, 0, 0)),
    # THT parts whose pads match KiCad exactly -> no transform
    "SIP3_REG": ("Converter_DCDC.3dshapes/"
                 "Converter_DCDC_RECOM_R-78B-2.0_THT.step", 0, (0, 0, 0)),
    "CP_D8_P3.5": ("Capacitor_THT.3dshapes/"
                   "CP_Radial_D8.0mm_P3.50mm.step", 0, (0, 0, 0)),
    # Phoenix MSTBVA stands in for the vertical WJ2EDGV terminal blocks
    # (same 5.08 pitch,
    # pin 1 at origin). Model file varies by pin count.
    "MKDS_2": ("Connector_Phoenix_MSTB.3dshapes/"
               "PhoenixContact_MSTBVA_2,5_2-G-5,08_1x02_P5.08mm_Vertical.step",
               0, (0, 0, 0)),
    "MKDS_3": ("Connector_Phoenix_MSTB.3dshapes/"
               "PhoenixContact_MSTBVA_2,5_3-G-5,08_1x03_P5.08mm_Vertical.step",
               0, (0, 0, 0)),
    "MKDS_4": ("Connector_Phoenix_MSTB.3dshapes/"
               "PhoenixContact_MSTBVA_2,5_4-G-5,08_1x04_P5.08mm_Vertical.step",
               0, (0, 0, 0)),
    "MKDS_5": ("Connector_Phoenix_MSTB.3dshapes/"
               "PhoenixContact_MSTBVA_2,5_5-G-5,08_1x05_P5.08mm_Vertical.step",
               0, (0, 0, 0)),
    # opto: SO-4 is a rough body stand-in for the LTV-817S SOP-4 (our pads are
    # a tall 2.54x6.5 quad vs KiCad's wide SO-4, so rotate + recentre on body).
    "SOP4_OPTO": ("Package_SO.3dshapes/SO-4_4.4x4.3mm_P2.54mm.step",
                  R90, (1.27, 3.25, 0)),
}

def build_footprint(ref, comp):
    fpdef = FOOTPRINTS[comp["footprint"]]
    x, y, ang = comp["at"]
    fp = Footprint(libraryNickname="sauna", entryName=comp["footprint"],
                   layer="F.Cu", tstamp=uid("fp", ref),
                   position=Position(X=x, Y=y, angle=ang if ang else None))
    has_tht = any(p[1] == "thru_hole" for p in fpdef["pads"])
    is_tp = comp["footprint"] == "TESTPOINT"   # bare probe pad, not a placed part
    fp.attributes = Attributes(
        type="through_hole" if has_tht else "smd",
        # JLC assembles SMD *and* THT, so both must appear in the CPL; only the
        # bare test pads are excluded from placement + assembly BOM.
        excludeFromPosFiles=is_tp, excludeFromBom=is_tp)
    lcsc = lcsc_for(comp["footprint"], comp["value"])   # LCSC part # on the
    if lcsc:                                            # footprint (board-side
        fp.properties["LCSC"] = lcsc                    # JLC tools read this)
    cx1, cy1, cx2, cy2 = fpdef["courtyard"]
    # reference + value on silkscreen / fab
    # Reference designators live on F.Fab (assembly drawing), not silk -- the
    # physical silkscreen carries only installer-facing functional labels.
    fp.graphicItems.append(FpText(
        type="reference", text=ref,
        position=Position(X=(cx1 + cx2) / 2, Y=cy1 - 1.0,
                          angle=-ang if ang else None),
        layer="F.Fab", effects=fp_effects(0.9, 0.13),
        tstamp=uid("ref", ref)))
    fp.graphicItems.append(FpText(
        type="value", text=comp["value"],
        position=Position(X=(cx1 + cx2) / 2, Y=cy2 + 1.2,
                          angle=-ang if ang else None),
        layer="F.Fab", effects=fp_effects(0.8, 0.12),
        tstamp=uid("val", ref)))
    # courtyard rectangle + fab outline
    fp.graphicItems.append(FpRect(
        start=Position(X=cx1, Y=cy1), end=Position(X=cx2, Y=cy2),
        layer="F.CrtYd", width=0.05, fill="none",
        tstamp=uid("crt", ref)))
    fp.graphicItems.append(FpRect(
        start=Position(X=cx1, Y=cy1), end=Position(X=cx2, Y=cy2),
        layer="F.Fab", width=0.1, fill="none", tstamp=uid("fab", ref)))
    if fpdef.get("pol"):  # pin-1 / polarity dot on silk
        p1 = fpdef["pads"][0]
        fp.graphicItems.append(FpRect(
            start=Position(X=p1[3][0] - 0.4, Y=cy1 - 0.5),
            end=Position(X=p1[3][0] + 0.4, Y=cy1 - 0.4),
            layer="F.SilkS", width=0.12, fill="solid",
            tstamp=uid("pol", ref)))

    for pad in fpdef["pads"]:
        num, ptype, shape, (px, py), (sx, sy), drill = pad
        net_name = comp["nets"].get(num)
        if ptype == "smd":
            layers = ["F.Cu", "F.Paste", "F.Mask"]
        else:
            layers = ["*.Cu", "*.Mask"]
        p = Pad(number=num, type=ptype,
                shape=shape if shape != "roundrect" else "roundrect",
                position=Position(X=px, Y=py, angle=ang if ang else None),
                size=Position(X=sx, Y=sy),
                layers=layers, tstamp=uid("pad", ref, num))
        if shape == "roundrect":
            p.roundrectRatio = 0.25
        if drill:
            p.drill = DrillDefinition(diameter=drill)
        if net_name:
            p.net = Net(number=NET_NUMBERS[net_name], name=net_name)
        fp.pads.append(p)
    model = MODELS.get(comp["footprint"])    # 3D body for the KiCad viewer
    if model:
        rel, rz, (ox, oy, oz), *rest = model
        sx, sy, sz = rest[0] if rest else (1, 1, 1)
        fp.models.append(Model(path=f"{MODEL_DIR}/{rel}",
                               pos=Coordinate(ox, oy, oz),
                               scale=Coordinate(sx, sy, sz),
                               rotate=Coordinate(0, 0, rz)))
    return fp


def mounting_hole(i, x, y):
    fp = Footprint(libraryNickname="sauna", entryName="MountingHole_M3_NPTH",
                   layer="F.Cu", tstamp=uid("hole", i),
                   position=Position(X=x, Y=y))
    fp.attributes = Attributes(type="through_hole", boardOnly=True,
                               excludeFromPosFiles=True, excludeFromBom=True)
    fp.graphicItems.append(FpText(
        type="reference", text=f"H{i}", position=Position(X=0, Y=-4.5),
        layer="F.SilkS", effects=fp_effects(0.8, 0.12), hide=True,
        tstamp=uid("href", i)))
    fp.graphicItems.append(FpText(
        type="value", text="M3", position=Position(X=0, Y=4.5),
        layer="F.Fab", effects=fp_effects(0.8, 0.12),
        tstamp=uid("hval", i)))
    fp.pads.append(Pad(
        number="", type="np_thru_hole", shape="circle",
        position=Position(X=0, Y=0),
        size=Position(X=MOUNTING_HOLE["drill"], Y=MOUNTING_HOLE["drill"]),
        drill=DrillDefinition(diameter=MOUNTING_HOLE["drill"]),
        layers=["*.Cu", "*.Mask"], tstamp=uid("hpad", i)))
    return fp


def board_outline(b):
    W, H, r = BOARD["width"], BOARD["height"], BOARD["corner_radius"]
    lines = [((r, 0), (W - r, 0)), ((W, r), (W, H - r)),
             ((W - r, H), (r, H)), ((0, H - r), (0, r))]
    for i, (s, e) in enumerate(lines):
        b.graphicItems.append(GrLine(
            start=Position(X=s[0], Y=s[1]), end=Position(X=e[0], Y=e[1]),
            layer="Edge.Cuts", width=0.1, tstamp=uid("edge", i)))
    k = r - r / math.sqrt(2)
    arcs = [((r, 0), (k, k), (0, r)),
            ((W, r), (W - k, k), (W - r, 0)),
            ((W - r, H), (W - k, H - k), (W, H - r)),
            ((0, H - r), (k, H - k), (r, H))]
    for i, (s, m, e) in enumerate(arcs):
        b.graphicItems.append(GrArc(
            start=Position(X=s[0], Y=s[1]), mid=Position(X=m[0], Y=m[1]),
            end=Position(X=e[0], Y=e[1]),
            layer="Edge.Cuts", width=0.1, tstamp=uid("arc", i)))


SILK_EDGE = 0.3        # keep silk this far off the board edge / corner arcs

# Installer-facing pin labels per connector, in pin order. Validated against
# the netlist at build time so they can't silently drift from the wiring.
CONN_LABELS = {
    "J_PWR":     ["+24V", "GND"],
    "J_LED":     ["R-", "G-", "B-", "W-", "+24V"],
    "J_PANEL":   ["+5V", "GND", "TX", "RX"],
    "J_DOOR":    ["DOOR", "GND"],
    "J_BENCH":   ["+3V3", "DATA", "GND"],
    "J_CEILING": ["+3V3", "DATA", "GND"],
    "J_COIL":    ["COIL+", "COIL-"],
    "J_RELAY_FB": ["+24V", "FB"],
    "J_AUX_OUT": ["+24V", "AUX-"],
    "J_SRL250":  ["OUT", "RETURN"],
    # J_SPARE is an internal optional 2.54mm header, not a field terminal
    # block -- it gets a plain label below, not a boxed panel.
}
# Installer-facing header text (renamed in KiCad to read on the cabinet wall).
CONN_HEADER = {
    "J_PWR": "24V IN", "J_LED": "LED LIGHTS", "J_PANEL": "CONTROLLER PANEL",
    "J_DOOR": "DOOR", "J_BENCH": "BENCH TEMP", "J_CEILING": "CEILING TEMP",
    "J_COIL": "RELAY COIL", "J_RELAY_FB": "RELAY MONITOR", "J_AUX_OUT": "AUX OUT",
    "J_SRL250": "HIGH TEMP",
}
TP_LABELS = {  # test point ref -> probed function (debug/bring-up)
    "TP2": "+5V", "TP3": "+3V3", "TP15": "RELAYFB",
}
LED_LABELS = {"LED1": "24V", "LED2": "5V", "LED3": "FAULT"}
# branch-protection rating labels, relative to the PTC center.
FUSE_LABELS = {
    "F1": ("LEDs (3A)", 0.436, 6.288, 0),
    "F2": ("HTR COIL (.75A)", 0.256, 4.570, 0),
    "F3": ("LOGIC (.75A)", 0.258, 4.570, 0),
    "F4": ("AUX (2A)", -0.002, 6.228, 0),
}

# Hand-nudged connector-box silk offsets, in design coordinates. These move
# the courtesy boxes toward the board edges without moving the terminal labels.
CONN_BOX_OFFSETS = {
    "J_PWR": (0.0, 0.404),
    "J_LED": (0.804, 0.0),
    "J_COIL": (-0.517, -0.03),
    "J_RELAY_FB": (-0.517, -0.03),
    "J_AUX_OUT": (0.0, 0.771),
    "J_PANEL": (0.0, -0.678),
    "J_DOOR": (0.0, -0.678),
    "J_BENCH": (0.0, -0.678),
    "J_CEILING": (0.0, -0.678),
    "J_SRL250": (0.0, -0.678),
}

# Per-connector body-side box padding. This lets edge connectors keep the
# readable three-band label style without letting the courtesy box hang off the
# board outline.
CONN_BODY_PAD = {
    "J_PWR": 0.274,
    "J_LED": 1.182,
}

# Hand nudges of silk labels, captured from KiCad and applied by place()/emit().
# Keyed by the label's stable uid("silk", ...) (preserved across a drag), value
# is (x, y, rot) in DESIGN coords (board pos - page_origin). Re-capture after
# moving labels in KiCad with: tools/_silk_diff.py
SILK_OVERRIDES = {
    # ESP module / board orientation labels (stable anchors)
    "4bdee42f-d190-5d75-9265-6a408ab43be6": (67.42, 51.718, 0),   # -> USB
    "50c6d573-b498-5ae4-a6f3-4ba5585954e0": (67.42, 51.718, 0),   # -> USB, after ESP box edge move
    "99ae89fb-7d1e-5c29-a10e-7b0b8e2d7742": (36.94, 51.718, 0),   # ANT <-
    "64cca8b7-92ec-5500-9b25-be9d82801fea": (3.158, 59.548, 90),  # title
    "ff63dbc7-d485-58cd-9751-1e2c10bbe6a4": (3.158, 59.548, 90),   # title, after ESP box edge move
    "0d89fb76-1c8d-575c-8ab1-f724bde587ec": (52.18, 51.718, 0),   # ESP32 DevKitC
    "31f11461-830a-5a4f-b1c2-a8ae64f767d7": (52.18, 51.718, 0),   # ESP32 DevKitC, after ESP box edge move
    # indicator-LED status labels
    "380c9830-254c-5c9a-b7ea-1f1ace23c669": (111.241, 2.0, 0),    # 24V
    "2b617ebe-ac3f-5505-a1fb-a9b4d8501014": (110.86, 6.0, 0),     # 5V
    "93036f90-517e-515a-a260-df093c64014c": (111.87, 10.0, 0),    # FAULT
    "3c0f49aa-10c1-5e1c-aed7-91fb006638df": (110.6, 7.478, 0),    # 24V, after LED cluster move
    "2c35f813-498a-5568-87ad-11e11ad2b585": (110.6, 11.542, 0),   # 5V, after LED cluster move
    "77fb491a-a1c1-57b7-bad6-7482e842df1f": (110.6, 15.606, 0),   # FAULT, after LED cluster move
    # --- 2026-06-15/16 hand-nudges captured from KiCad (tools/_silk_diff.py).
    #     +3V3/+5V uids track TP2/TP3, recomputed after test-point moves. ---
    "2d782a89-1422-569e-a752-74f8d0a4c92a": (106.79, 45.07, 0),   # COIL\nACTIVE (2-line; uid recomputed for relay-feedback inset move)
    "05455324-ac02-5201-b959-986ce49ca3e4": (106.79, 45.07, 0),   # COIL\nACTIVE, after J_RELAY_FB move
    "c13beb62-1db6-58da-b98f-d32bcc77f5fb": (106.79, 45.07, 0),   # COIL\nACTIVE, after relay monitor nudge
    "6f86c205-00e8-54b7-8c6f-a3271fa6e44c": (92.82, 68.67, 0),    # +3V3 (TP3)
    "9d4f2323-9d57-5e32-90f6-19642bc78e46": (96.63, 68.67, 0),    # +5V (TP2)
    "dbfb0980-8558-53dc-8afd-a2a2f12f0cf2": (94.725, 64.606, 0),  # TEST POINTS
    "b71b0c09-a770-5d47-afd7-2b9e3cefdbdb": (16.62, 51.928, 0),   # ANTENNA\nZONE
    "f6a1c92a-032e-5fee-bbc3-0261719dfb34": (16.62, 51.928, 0),   # ANTENNA\nZONE, after keepout move
    "8754e72f-e9be-5973-8b3f-4d9a9d3b324f": (83.676, 1.636, 0),   # HTR COIL (1A)
    "53f71b84-35a4-550f-af88-ebc8008b7962": (83.676, 1.636, 0),   # HTR COIL (1A), after F2 move
    "1cfea3e3-0f9f-5888-8d1f-3579dcfceeae": (72.0, 1.636, 0),     # LEDs (5A MAX)
    "4fad4e62-26ce-55f6-b210-cff2d8e6c425": (95.106, 1.636, 0),   # LOGIC (1A)
    "be97dca6-9074-5d9a-afa2-e9f8268684df": (95.106, 1.636, 0),   # LOGIC (1A), after F3 move
    # --- 2026-06-16 edge-connector inset captured from KiCad.
    #     Preserve the hand-placed connector boxes/pin labels around them. ---
    "7ba45bb5-f225-5ac4-b59e-b4ed454f3e06": (11.690, 32.420, 90),  # +24V
    "34246f23-aafc-5206-a39a-e57a3eb96b15": (57.260, 11.780, 0),   # +24V
    "60e4e471-ba42-5e58-adbc-2e4a45f3b58a": (100.440, 76.690, 0),  # +24V
    "f3a120a9-5025-5087-b0d3-400c5ddb2eaf": (108.700, 59.070, 90), # +24V
    "a0fb6c5a-3fb2-54cd-a4f7-618c7f67db3b": (55.960, 76.690, 0),   # +3V3
    "fb60afb7-c768-57f9-8507-5ed06ac59065": (77.550, 76.690, 0),   # +3V3
    "96b2c8d5-560f-54ad-9f05-d1ad71b27346": (12.780, 76.690, 0),   # +5V
    "dff60bee-41e4-54d4-9e3f-e3f8cc1f7a8f": (59.800, 14.460, 0),   # 24V IN
    "baf26fe4-bbc0-580d-ab0a-8c4a984c4290": (108.700, 53.990, 90), # old AUX label
    "04bcd421-39ed-5a6b-87a4-c17b742356ff": (11.690, 22.260, 90),  # B-
    "86ffd390-f985-5a46-91b8-aec27a9bcfe7": (61.040, 74.010, 0),   # BENCH TEMP
    "c8509f9d-5791-5150-aff7-1c6934807a12": (82.630, 74.010, 0),   # CEILING TEMP
    "e702af25-1d5c-59d6-bb20-f4976ff228d6": (108.800, 38.690, 90), # COIL+
    "40233ec5-cac5-57d4-bb85-3c3cd2a4c3f9": (108.800, 33.610, 90), # COIL-
    "eb61a2d7-9a5e-5815-88bb-e74aa26d7ad8": (20.400, 74.010, 0),   # CONTROLLER
    "5126102e-e6a4-5e26-9256-ca020c4cca0a": (61.040, 76.690, 0),   # DATA
    "8a829502-9369-5e60-8667-7cd270f5b0a2": (82.630, 76.690, 0),   # DATA
    "3e152814-2929-5d20-8ab3-b63b80e897db": (41.510, 73.770, 0),   # DOOR
    "3b9c7059-b200-57e8-9db7-f2a7c2a862d6": (38.810, 76.570, 0),   # DOOR
    "15123a8a-2f24-5114-b11a-f22345325835": (11.690, 17.180, 90),  # G-
    "66a4bc1a-d406-5eb6-abdc-b6c847c56872": (17.860, 76.690, 0),   # GND
    "dcec4cee-1e2a-5780-85f3-cb2767b7fd7a": (43.890, 76.690, 0),   # GND
    "32d7c704-1450-5fee-8d3e-e39e8873d2a6": (62.340, 11.780, 0),   # GND
    "2bd3cd86-5c15-5d1e-a3f7-981c8b374ee4": (66.120, 76.690, 0),   # GND
    "7f397f32-9ef9-5f37-90a8-ca7ade2f48cc": (87.710, 76.690, 0),   # GND
    "3162ff94-5513-5c2d-9441-a3b8271b845f": (14.370, 22.260, 90),  # LED LIGHTS
    "93455558-427f-5211-817c-fe8bb69dc75b": (11.690, 12.100, 90),  # R-
    "dc2ab25e-e9ee-5425-9ccb-8a82f38c8a28": (106.030, 56.530, 90), # old RELAY AUX label
    "ce334d04-457b-5422-bcfa-2016445faf77": (106.120, 36.150, 90), # RELAY COIL
    "bbee3c45-7414-5f66-96fd-5db8af4fdb52": (105.520, 76.690, 0),  # RTN
    "ee236c27-c53a-5bf7-ba3d-670dd279fb1a": (28.020, 76.690, 0),   # RX
    "cde40ab2-760a-57bc-956d-f206430d51ae": (102.980, 73.265, 0),  # HIGH TEMP
    "cbfbbae5-6169-5957-9a1f-35046ddacd89": (22.940, 76.690, 0),   # TX
    "340ff708-e41b-5f05-a10b-5733447cced8": (11.690, 27.340, 90),  # W-
}


def _text_rect(text, x, y, size, rot=0):
    """approx silk text bounding box centred on (x, y); rot=90 swaps w/h"""
    w = len(text) * size * 0.72 + 0.3
    h = size * 1.05 + 0.2
    if rot:
        w, h = h, w
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def _overlap(a, bx):
    return not (a[2] <= bx[0] or bx[2] <= a[0] or
                a[3] <= bx[1] or bx[3] <= a[1])


def _edge_clear(rect):
    """True if rect keeps SILK_EDGE off every board edge incl. corner arcs"""
    W, H, r = BOARD["width"], BOARD["height"], BOARD["corner_radius"]
    if rect[0] < SILK_EDGE or rect[1] < SILK_EDGE or \
       rect[2] > W - SILK_EDGE or rect[3] > H - SILK_EDGE:
        return False
    for ccx, ccy, sx, sy in ((r, r, -1, -1), (W - r, r, 1, -1),
                             (r, H - r, -1, 1), (W - r, H - r, 1, 1)):
        cx = rect[0] if sx < 0 else rect[2]
        cy = rect[1] if sy < 0 else rect[3]
        if (cx < ccx if sx < 0 else cx > ccx) and \
           (cy < ccy if sy < 0 else cy > ccy):
            if math.hypot(cx - ccx, cy - ccy) > r - SILK_EDGE:
                return False
    return True


def _body_bbox(comp):
    """world-space bounding box of a footprint's courtyard (its body)"""
    x, y, ang = comp["at"]
    x1, y1, x2, y2 = FOOTPRINTS[comp["footprint"]]["courtyard"]
    cs = [rot(px, py, ang) for px, py in
          [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]]
    xs = [x + c[0] for c in cs]
    ys = [y + c[1] for c in cs]
    return (min(xs), min(ys), max(xs), max(ys))


def _occupied_rects():
    """copper-pad mask rects + existing silk dots a label must avoid"""
    rects = []
    for ref in sorted(C):
        comp = C[ref]
        fpdef = FOOTPRINTS[comp["footprint"]]
        for pad in fpdef["pads"]:
            num, ptype, shape, (px, py), (sx, sy), drill = pad
            cx, cy = pad_abs(comp, pad)
            hx, hy = sx / 2, sy / 2
            if comp["at"][2] % 180 == 90:
                hx, hy = hy, hx
            rects.append((cx - hx - 0.1, cy - hy - 0.1,
                          cx + hx + 0.1, cy + hy + 0.1))
        if fpdef.get("pol"):           # pin-1 polarity dot (stays on silk)
            cx, cy = pad_abs(comp, fpdef["pads"][0])
            rects.append((cx - 0.6, cy - 0.9, cx + 0.6, cy + 0.1))
    return rects


def silk_labels(b):
    occupied = _occupied_rects()
    placed = []
    W, H = BOARD["width"], BOARD["height"]
    emitted = [0]

    def place(text, x0, y0, size, pushes, span=6.0, center=False):
        """find the nearest candidate offset where text clears pads, the
        board edge and other labels; emit it. pushes = preferred directions.
        center=True keeps the label on its axis (no perpendicular nudge) so it
        stays centred on the pin/footprint -- only the push offset is searched."""
        u = uid("silk", text, x0, y0)
        if u in SILK_OVERRIDES:                     # user dragged it in KiCad
            ox, oy, orot = SILK_OVERRIDES[u]
            b.graphicItems.append(GrText(
                text=text, position=Position(X=round(ox, 3), Y=round(oy, 3),
                                             angle=orot or None),
                layer="F.SilkS",
                effects=Effects(font=Font(height=size, width=size,
                                thickness=round(size * 0.15, 3))),
                tstamp=u))
            placed.append(_text_rect(text, ox, oy, size, orot))
            emitted[0] += 1
            return True
        steps = [round(s * 0.4, 2) for s in range(int(span / 0.4) + 1)]
        perps = [0] if center else [0, 0.7, -0.7, 1.4, -1.4]
        for d in steps:
            for ux, uy in pushes:
                # perpendicular to the push direction, to slot between pads
                qx, qy = -uy, ux
                for q in perps:
                    x = x0 + ux * d + qx * q
                    y = y0 + uy * d + qy * q
                    rect = _text_rect(text, x, y, size)
                    if not _edge_clear(rect):
                        continue
                    if any(_overlap(rect, o) for o in occupied):
                        continue
                    if any(_overlap(rect, p) for p in placed):
                        continue
                    b.graphicItems.append(GrText(
                        text=text, position=Position(X=round(x, 3),
                                                     Y=round(y, 3)),
                        layer="F.SilkS",
                        effects=Effects(font=Font(height=size, width=size,
                                        thickness=round(size * 0.15, 3))),
                        tstamp=uid("silk", text, x0, y0)))
                    placed.append(rect)
                    emitted[0] += 1
                    return True
        print(f"  !! silk: could not place '{text}' near ({x0},{y0})")
        return False

    def line(x1, y1, x2, y2, w=0.15):
        b.graphicItems.append(GrLine(
            start=Position(X=round(x1, 2), Y=round(y1, 2)),
            end=Position(X=round(x2, 2), Y=round(y2, 2)),
            layer="F.SilkS", width=w, tstamp=uid("ln", x1, y1, x2, y2)))
        # register the line as a thin obstacle so place()'d text avoids it
        placed.append((min(x1, x2) - 0.25, min(y1, y2) - 0.25,
                       max(x1, x2) + 0.25, max(y1, y2) + 0.25))

    def box(x1, y1, x2, y2, w=0.15):
        line(x1, y1, x2, y1, w)
        line(x2, y1, x2, y2, w)
        line(x2, y2, x1, y2, w)
        line(x1, y2, x1, y1, w)

    def emit(text, x, y, size, rot=0):          # direct, exact placement
        u = uid("silk", text, round(x, 2), round(y, 2))
        if u in SILK_OVERRIDES:                     # user dragged it in KiCad
            x, y, rot = SILK_OVERRIDES[u]
        b.graphicItems.append(GrText(
            text=text, position=Position(X=round(x, 3), Y=round(y, 3),
                                         angle=rot or None),
            layer="F.SilkS",
            effects=Effects(font=Font(height=size, width=size,
                            thickness=round(size * 0.15, 3))),
            tstamp=u))
        placed.append(_text_rect(text, x, y, size, rot))
        emitted[0] += 1

    def interior_dir(cx, cy):
        d = {(1, 0): cx, (-1, 0): W - cx, (0, 1): cy, (0, -1): H - cy}
        return min(d, key=d.get)

    # ---- connector panels: boxed group, title header + pin labels --------
    # Each connector gets a courtesy box around the block + its labels, with a
    # title-header row (separated by a divider line) carrying the group name
    # centred on the footprint, and pin labels centred on their pins -- all on
    # the interior side, clear of the block body so they read with wires in.
    HDR = 3.05      # title-header band depth
    PINB = 2.28     # pin-label band depth
    BODYB = 0.80    # extra box breathing room on the terminal-body side
    for ref, labels in CONN_LABELS.items():
        if ref not in C:
            continue
        comp = C[ref]
        pads = sorted(FOOTPRINTS[comp["footprint"]]["pads"],
                      key=lambda p: int(p[0]) if str(p[0]).isdigit() else 0)
        assert len(labels) == len(pads), \
            f"{ref}: {len(labels)} labels vs {len(pads)} pads"
        cx, cy = comp["at"][0], comp["at"][1]
        ux, uy = interior_dir(cx, cy)               # toward board centre
        bx1, by1, bx2, by2 = _body_bbox(comp)       # terminal-block body
        hdr = CONN_HEADER[ref]
        box_dx, box_dy = CONN_BOX_OFFSETS.get(ref, (0.0, 0.0))
        bodyb = CONN_BODY_PAD.get(ref, BODYB)
        if uy:                                      # BOTTOM/TOP: horizontal box
            bl, br = bx1 - 0.8, bx2 + 0.8           # box spans body width + .8
            edge = (by2 if uy < 0 else by1) - uy * (0.01 + bodyb)
            inner = by1 if uy < 0 else by2          # body's interior edge
            top = inner + uy * (HDR + PINB)         # box interior end
            div = inner + uy * PINB                 # title/pin divider
            box(bl + box_dx, min(edge, top) + box_dy,
                br + box_dx, max(edge, top) + box_dy)
            line(bl + box_dx, div + box_dy, br + box_dx, div + box_dy)
            line(bl + box_dx, inner + box_dy, br + box_dx, inner + box_dy)
            emit(hdr, (bl + br) / 2 + box_dx, top - uy * HDR / 2 + box_dy, 1.1)
            for pad, lab in zip(pads, labels):
                px, _ = pad_abs(comp, pad)
                emit(lab, px + box_dx, inner + uy * (PINB / 2) + box_dy, 0.8)
        else:                                       # LEFT/RIGHT: rotated 90
            bl, br = by1 - 0.8, by2 + 0.8           # box spans body height + .8
            edge = (bx2 if ux < 0 else bx1) - ux * (0.01 + bodyb)
            inner = bx1 if ux < 0 else bx2
            far = inner + ux * (HDR + PINB)
            div = inner + ux * PINB
            box(min(edge, far) + box_dx, bl + box_dy,
                max(edge, far) + box_dx, br + box_dy)
            line(div + box_dx, bl + box_dy, div + box_dx, br + box_dy)
            line(inner + box_dx, bl + box_dy, inner + box_dx, br + box_dy)
            emit(hdr, far - ux * HDR / 2 + box_dx, (bl + br) / 2 + box_dy, 1.1, rot=90)
            for pad, lab in zip(pads, labels):
                _, py = pad_abs(comp, pad)
                emit(lab, inner + ux * (PINB / 2) + box_dx, py + box_dy, 0.8, rot=90)

    # ---- design graphics: courtesy outlines (drawn FIRST so text avoids) --
    # All derived from the layout so they track component/board moves.
    kx1, ky1, kx2, ky2 = BOARD["antenna_keepout"]
    e1, e2 = _body_bbox(C["J_ESP1"]), _body_bbox(C["J_ESP2"])  # ESP module
    ex1, ey1 = min(e1[0], e2[0]) - 2.4, min(e1[1], e2[1]) - 0.4
    ex2, ey2 = max(e1[2], e2[2]) + 0.48, max(e1[3], e2[3]) + 0.4
    # Combined antenna/ESP outline: antenna keepout at left, ESP module at
    # right, with one divider line. The actual copper keepout remains the zone.
    box(kx1, ey1, ex2, ey2)
    line(kx2, ey1, kx2, ey2)
    # Branch-protection group box, hand-spaced in KiCad for the compact PTC
    # block. Coordinates are design-space; board page origin is applied later.
    box(68.94, 0.37, 89.01, 27.04)
    line(68.94, 3.67, 89.01, 3.67)
    line(68.82, 16.88, 88.88, 16.88)

    # ---- test points (probe function), indicator LEDs, fuse ratings ------
    for ref, lab in TP_LABELS.items():
        if ref in C:
            px, py = pad_abs(C[ref], FOOTPRINTS[C[ref]["footprint"]]["pads"][0])
            place(lab, px, py - 1.8, 0.8,
                  [(0, -1), (0, 1), (1, 0), (-1, 0)], span=4.0)
    for ref, lab in LED_LABELS.items():
        if ref in C:
            px, py = pad_abs(C[ref], FOOTPRINTS[C[ref]["footprint"]]["pads"][0])
            place(lab, px - 3.0, py, 0.8,
                  [(-1, 0), (1, 0), (0, -1), (0, 1)], span=5.0)
    for ref, (lab, dx, dy, text_rot) in FUSE_LABELS.items():
        if ref in C:
            cx, cy = C[ref]["at"][0], C[ref]["at"][1]
            emit(lab, cx + dx, cy + dy, 0.8, rot=text_rot)
    emit("FUSES", 78.85, 2.14, 1.0)
    # RGBW channel IDs above each LED MOSFET (the activity LED + gate resistors
    # fill the column below, so the channel letter heads it from the top).
    for ref, ch in (("Q2", "R"), ("Q3", "G"), ("Q4", "B"), ("Q5", "W")):
        if ref in C:
            cx, cy = C[ref]["at"][0], C[ref]["at"][1]
            emit(ch, cx, cy - 6.03, 1.0)

    # ---- notes & orientation text (positions derived from the boxes) -----
    ecx, ecy = (ex1 + ex2) / 2, (ey1 + ey2) / 2   # ESP box centre
    kcx, kcy = (kx1 + kx2) / 2, (ky1 + ky2) / 2   # keepout centre
    place(f"{TITLE}  REV {REV}", ecx, ey1 - 3, 1.3, [(0, -1), (0, 1)], span=6.0)
    # Antenna zone: compact two-line label inside the keepout box.
    place("ANTENNA\\nZONE", kcx, kcy - 3, 0.9, [(0, -1), (0, 1)], span=6.0, center=True)
    # ESP orientation: antenna end (left, toward keepout) vs USB end (right)
    place("ESP32 DevKitC", ecx, ecy, 1.0, [(0, -1), (0, 1)], span=4.0,
          center=True)
    place("ANT <-", ex1 + 5, ecy, 0.9, [(0, -1), (0, 1)], span=3.0, center=True)
    place("-> USB", ex2 - 5, ecy, 0.9, [(0, -1), (0, 1)], span=3.0, center=True)
    if "J_RELAY_FB" in C:
        ax, ay = C["J_RELAY_FB"]["at"][0], C["J_RELAY_FB"]["at"][1]
        place("COIL\\nACTIVE", ax - 12, ay + 11, 0.8,   # \n = KiCad 2-line escape
              [(0, 1), (0, -1), (-1, 0)], span=6.0)
    if "OPT_RELAY_FB" in C:
        emit("OPT 1 (RELAY FB)", 86.47, 45.959, 0.8)
    if "OPT2" in C:
        emit("OPT 2 (HIGH TEMP)", 85.96, 55.99, 0.8)
    emit("LEDS", 33.64, 5.19, 0.8)
    if "Q1" in C:
        emit("COIL", 107.81, 20.94, 0.8)
    if "Q6" in C:
        emit("AUX", 93.33, 23.99, 0.8)
    if "J_SPARE" in C:                          # internal header: plain label
        sx, sy = C["J_SPARE"]["at"][0], C["J_SPARE"]["at"][1]
        place("SPARE IN", sx, sy - 3.2, 0.8,
              [(0, -1), (0, 1), (1, 0), (-1, 0)], span=5.0)
    tps_ = [C[r]["at"] for r in ("TP2", "TP3") if r in C]
    if tps_:                                     # group header over the test pts
        emit("TEST POINTS", sum(p[0] for p in tps_) / len(tps_),
             min(p[1] for p in tps_) - 3.18, 0.9)

    print(f"  silk: placed {emitted[0]} labels, "
          f"{len(placed)} rects, 0 collisions by construction")


def zones(b):
    W, H = BOARD["width"], BOARD["height"]
    kx1, ky1, kx2, ky2 = BOARD["antenna_keepout"]

    def poly(points):
        return ZonePolygon(coordinates=[Coordinate(X=p[0], Y=p[1])
                                        for p in points])
    # Solid GND plane on B.Cu (KiCad refills on open; zone outline = board)
    gnd = Zone(net=NET_NUMBERS["GND"], netName="GND", layers=["B.Cu"],
               tstamp=uid("zone-gnd"), name="GND_PLANE",
               hatch=Hatch(style="edge", pitch=0.508),
               connectPads=Position(unlocked=False),
               minThickness=0.25,
               fillSettings=FillSettings(yes=True, thermalGap=0.5,
                                         thermalBridgeWidth=0.5,
                                         islandRemovalMode=0),
               polygons=[poly([(0.6, 0.6), (W - 0.6, 0.6),
                               (W - 0.6, H - 0.6), (0.6, H - 0.6)])])
    gnd.connectPads = None  # default thru-relief connection
    b.zones.append(gnd)
    # Antenna keepout: both copper layers, no copper pour/tracks/vias
    keep = Zone(layers=["F.Cu", "B.Cu"], tstamp=uid("zone-keepout"),
                name="ANTENNA_KEEPOUT", net=0, netName="",
                hatch=Hatch(style="full", pitch=0.508),
                minThickness=0.25,
                keepoutSettings=KeepoutSettings(
                    tracks="not_allowed", vias="not_allowed",
                    pads="not_allowed", copperpour="not_allowed",
                    footprints="not_allowed"),
                polygons=[poly([(kx1, ky1), (kx2, ky1),
                                (kx2, ky2), (kx1, ky2)])])
    b.zones.append(keep)


def traces(b):
    for i, (net, layer, width, pts) in enumerate(routing.ROUTES):
        for j in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[j], pts[j + 1]
            b.traceItems.append(Segment(
                start=Position(X=x1, Y=y1), end=Position(X=x2, Y=y2),
                width=width, layer=layer, net=NET_NUMBERS[net],
                tstamp=uid("seg", i, j)))
    for i, (net, (x, y)) in enumerate(routing.VIAS):
        b.traceItems.append(Via(
            position=Position(X=x, Y=y), size=0.8, drill=0.4,
            layers=["F.Cu", "B.Cu"], net=NET_NUMBERS[net],
            tstamp=uid("via", i)))


def translate_board(b, dx, dy):
    """Shift every item by (dx, dy) -- used to place the board where it sits on
    the editor sheet. Geometry is generated at origin; this only repositions
    the finished board (no effect on fab, which is relative to Edge.Cuts)."""
    def mv(p):
        if p is not None:
            p.X = round(p.X + dx, 4)
            p.Y = round(p.Y + dy, 4)
    for fp in b.footprints:                      # pads/graphics are relative
        mv(fp.position)
    for g in b.graphicItems:
        for a in ("start", "mid", "end", "position"):
            mv(getattr(g, a, None))
    for tr in b.traceItems:
        for a in ("start", "end", "position"):
            mv(getattr(tr, a, None))
    for z in b.zones:
        for poly in (z.polygons or []):
            for c in poly.coordinates:
                c.X = round(c.X + dx, 4)
                c.Y = round(c.Y + dy, 4)


def main():
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                       "sauna-rev-b.kicad_pcb"))
    b = Board.create_new()
    b.generator = "claude_pcb_tools"
    b.nets = [Net(number=0, name="")] + [
        Net(number=NET_NUMBERS[n], name=n) for n in sorted(NETS)]

    board_outline(b)
    for ref in sorted(C):
        b.footprints.append(build_footprint(ref, C[ref]))
    for i, (x, y) in enumerate(BOARD["mounting_holes"], start=1):
        b.footprints.append(mounting_hole(i, x, y))
    silk_labels(b)
    zones(b)
    traces(b)

    ox, oy = BOARD.get("page_origin", (0, 0))    # center on the editor sheet
    if ox or oy:
        translate_board(b, ox, oy)
    b.to_file(out)
    nseg = sum(1 for t in b.traceItems if isinstance(t, Segment))
    nvia = sum(1 for t in b.traceItems if isinstance(t, Via))
    print(f"wrote {out}: {len(b.footprints)} footprints, "
          f"{nseg} segments, {nvia} vias, {len(b.zones)} zones")
    back = Board.from_file(out)
    assert len(back.footprints) == len(b.footprints)
    print("round-trip parse OK")


if __name__ == "__main__":
    main()
