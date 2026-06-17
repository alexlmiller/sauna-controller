"""Footprint primitives for the Rev B board.

Each footprint is described abstractly; generate_board.py turns these into
kiutils Footprint objects. Pad positions are relative to the footprint origin
(rotation handled by the generator). All dimensions in mm.

pads: list of (number, type, shape, (x, y), (sx, sy), drill_or_None)
  type:  'smd' | 'thru_hole' | 'np_thru_hole'
  shape: 'rect' | 'roundrect' | 'circle' | 'oval'
courtyard: (x1, y1, x2, y2) bounding box used for silk + overlap checking
"""


def _smd2(pitch, px, py, shape="roundrect"):
    h = pitch / 2
    return [("1", "smd", shape, (-h, 0), (px, py), None),
            ("2", "smd", shape, (h, 0), (px, py), None)]


FOOTPRINTS = {
    # --- SMD passives ---
    "R_0805": dict(pads=_smd2(1.9, 1.0, 1.3),
                   courtyard=(-1.7, -0.95, 1.7, 0.95)),
    "C_0805": dict(pads=_smd2(1.9, 1.0, 1.3),
                   courtyard=(-1.7, -0.95, 1.7, 0.95)),
    "LED_0805": dict(pads=_smd2(1.9, 1.0, 1.3),
                     courtyard=(-1.7, -0.95, 1.7, 0.95), pol=True),
    "R_1206": dict(pads=_smd2(2.9, 1.15, 1.7),
                   courtyard=(-2.3, -1.15, 2.3, 1.15)),
    "C_1210": dict(pads=_smd2(2.9, 1.15, 2.7),
                   courtyard=(-2.3, -1.65, 2.3, 1.65)),
    "R_1812": dict(pads=_smd2(4.4, 1.5, 3.4),
                   courtyard=(-3.1, -2.0, 3.1, 2.0)),
    "PTC_1812": dict(pads=_smd2(4.4, 1.5, 3.4),
                     courtyard=(-3.1, -2.0, 3.1, 2.0)),
    "PTC_2920": dict(pads=_smd2(5.2, 2.6, 5.2),
                     courtyard=(-4.6, -3.2, 4.6, 3.2)),
    # --- SMD diodes (pin 1 = cathode) ---
    "D_SMA": dict(pads=_smd2(4.0, 2.5, 1.7),
                  courtyard=(-3.0, -1.6, 3.0, 1.6), pol=True),
    "D_SMB": dict(pads=_smd2(4.4, 2.5, 2.3),
                  courtyard=(-3.2, -1.9, 3.2, 1.9), pol=True),
    "D_SOD323": dict(pads=_smd2(2.3, 0.9, 0.8),
                     courtyard=(-1.75, -0.85, 1.75, 0.85), pol=True),
    "D_SOD923": dict(pads=_smd2(1.0, 0.5, 0.5),
                     courtyard=(-0.85, -0.55, 0.85, 0.55), pol=True),
    # --- DPAK MOSFET (1=G, 2=D tab, 3=S); leads at +y, tab at -y ---
    "TO252": dict(pads=[("1", "smd", "roundrect", (-2.28, 5.0), (1.4, 2.2), None),
                        ("3", "smd", "roundrect", (2.28, 5.0), (1.4, 2.2), None),
                        ("2", "smd", "rect", (0, -1.5), (6.0, 6.4), None)],
                  courtyard=(-3.6, -5.0, 3.6, 6.4)),
    # --- SOT-23-6 (USBLC6); pins 1-3 at +y left->right, 4-6 at -y r->l ---
    "SOT23_6": dict(pads=[("1", "smd", "roundrect", (-0.95, 1.3), (0.62, 1.2), None),
                          ("2", "smd", "roundrect", (0.0, 1.3), (0.62, 1.2), None),
                          ("3", "smd", "roundrect", (0.95, 1.3), (0.62, 1.2), None),
                          ("4", "smd", "roundrect", (0.95, -1.3), (0.62, 1.2), None),
                          ("5", "smd", "roundrect", (0.0, -1.3), (0.62, 1.2), None),
                          ("6", "smd", "roundrect", (-0.95, -1.3), (0.62, 1.2), None)],
                   courtyard=(-1.6, -2.1, 1.6, 2.1)),
    # --- SMD optocoupler (LTV-817S / EL357N-class, SOP-4 gull-wing).
    #     Same 1=A 2=K 3=E 4=C pinout + origin as the DIP-4 it replaces, so
    #     net mapping is unchanged. VERIFY land pattern vs the chosen LCSC part.
    "SOP4_OPTO": dict(pads=[("1", "smd", "roundrect", (0, 0), (1.1, 1.6), None),
                            ("2", "smd", "roundrect", (2.54, 0), (1.1, 1.6), None),
                            ("3", "smd", "roundrect", (2.54, -6.5), (1.1, 1.6), None),
                            ("4", "smd", "roundrect", (0, -6.5), (1.1, 1.6), None)],
                      courtyard=(-1.1, -7.6, 3.64, 1.1), pol=True),
    # --- THT ---
    "DIP4": dict(pads=[("1", "thru_hole", "rect", (0, 0), (1.6, 1.6), 0.8),
                       ("2", "thru_hole", "oval", (2.54, 0), (1.6, 1.6), 0.8),
                       ("3", "thru_hole", "oval", (2.54, -7.62), (1.6, 1.6), 0.8),
                       ("4", "thru_hole", "oval", (0, -7.62), (1.6, 1.6), 0.8)],
                 courtyard=(-1.6, -9.2, 4.1, 1.6), pol=True),
    "SIP3_REG": dict(pads=[("1", "thru_hole", "rect", (0, 0), (1.8, 1.8), 1.0),
                           ("2", "thru_hole", "circle", (2.54, 0), (1.8, 1.8), 1.0),
                           ("3", "thru_hole", "circle", (5.08, 0), (1.8, 1.8), 1.0)],
                     courtyard=(-3.3, -3.2, 8.4, 1.5)),
    "CP_D8_P3.5": dict(pads=[("1", "thru_hole", "rect", (0, 0), (1.8, 1.8), 0.9),
                             ("2", "thru_hole", "circle", (3.5, 0), (1.8, 1.8), 0.9)],
                       courtyard=(-2.5, -4.3, 6.0, 4.3), pol=True),
    "TESTPOINT": dict(pads=[("1", "smd", "circle", (0, 0), (1.5, 1.5), None)],
                      courtyard=(-1.0, -1.0, 1.0, 1.0)),
    "HDR_1x2": dict(pads=[("1", "thru_hole", "rect", (0, 0), (1.7, 1.7), 1.0),
                          ("2", "thru_hole", "oval", (0, 2.54), (1.7, 1.7), 1.0)],
                    courtyard=(-1.3, -1.3, 1.3, 3.9)),
}

# Phoenix MKDS 1,5/N-5,08 style terminal blocks: pins inline +x, 5.08 pitch.
# Body: 5.08*N wide (stackable), 9.6 deep; pin row centered, wires exit -y.
for n in (2, 3, 4, 5):
    pads = [("1", "thru_hole", "rect", (0, 0), (3.0, 3.0), 1.3)]
    for k in range(1, n):
        pads.append((str(k + 1), "thru_hole", "circle",
                     (5.08 * k, 0), (3.0, 3.0), 1.3))
    FOOTPRINTS[f"MKDS_{n}"] = dict(
        pads=pads, courtyard=(-3.04, -4.66, 5.08 * (n - 1) + 3.04, 5.2))

# 1x19 female socket row, 2.54 mm pitch along +x.
_p19 = [("1", "thru_hole", "rect", (0, 0), (1.7, 1.7), 1.0)]
for k in range(1, 19):
    _p19.append((str(k + 1), "thru_hole", "oval", (2.54 * k, 0), (1.7, 1.7), 1.0))
FOOTPRINTS["SOCKET_1x19"] = dict(
    pads=_p19, courtyard=(-1.6, -1.6, 2.54 * 18 + 1.6, 1.6))

MOUNTING_HOLE = dict(drill=3.2, pad=6.0)
