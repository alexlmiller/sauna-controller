#!/usr/bin/env python3
"""Generate claude-pcb/sauna-rev-b.kicad_pcb from tools/design.py + routing.py.

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

from kiutils.board import Board
from kiutils.footprint import Footprint, Pad, Attributes, DrillDefinition
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


def build_footprint(ref, comp):
    fpdef = FOOTPRINTS[comp["footprint"]]
    x, y, ang = comp["at"]
    fp = Footprint(libraryNickname="sauna", entryName=comp["footprint"],
                   layer="F.Cu", tstamp=uid("fp", ref),
                   position=Position(X=x, Y=y, angle=ang if ang else None))
    has_smd = any(p[1] == "smd" for p in fpdef["pads"])
    has_tht = any(p[1] == "thru_hole" for p in fpdef["pads"])
    fp.attributes = Attributes(
        type="through_hole" if has_tht else "smd",
        excludeFromPosFiles=has_tht, excludeFromBom=False)
    cx1, cy1, cx2, cy2 = fpdef["courtyard"]
    # reference + value on silkscreen / fab
    fp.graphicItems.append(FpText(
        type="reference", text=ref,
        position=Position(X=(cx1 + cx2) / 2, Y=cy1 - 1.0,
                          angle=-ang if ang else None),
        layer="F.SilkS", effects=fp_effects(0.9, 0.13),
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


def silk_labels(b):
    labels = [
        # group labels (text, x, y, size)
        ("24V IN", 16.5, 13.5, 1.5), ("LED RGBW", 44, 13.5, 1.5),
        ("COIL", 68.5, 13.5, 1.5), ("AUX FB", 84.5, 13.5, 1.5),
        ("PANEL", 25.5, 72.5, 1.5), ("SRL250", 48.5, 74.5, 1.5),
        ("DOOR", 63.5, 75.5, 1.5), ("BENCH", 82, 75.5, 1.5),
        ("CEILING", 107, 75.5, 1.5),
        ("FUSES: F3 LOGIC 1A F | F2 COIL 1A F | F1 LED 5A T", 51, 24.5, 1.2),
        ("ANTENNA KEEPOUT", 12, 52.5, 1.2),
        (f"{TITLE}  REV {REV}", 65, 51, 2.0),
        ("USB ->", 81, 52.5, 1.2),
        # per-pin labels, top edge connectors (above pin row)
        ("+24V", 14, 2.5, 0.8), ("0V", 19.1, 2.5, 0.8),
        ("R-", 34, 2.5, 0.8), ("G-", 39.1, 2.5, 0.8), ("B-", 44.2, 2.5, 0.8),
        ("W-", 49.2, 2.5, 0.8), ("V+", 54.3, 2.5, 0.8),
        ("C+", 66, 2.5, 0.8), ("C-", 71.1, 2.5, 0.8),
        ("A", 82, 2.5, 0.8), ("B", 87.1, 2.5, 0.8),
        # bottom edge connectors (below pin row)
        ("5V", 18, 82.5, 0.8), ("0V", 23.1, 82.5, 0.8),
        ("TX", 28.2, 82.5, 0.8), ("RX", 33.2, 82.5, 0.8),
        ("OUT", 46, 82.5, 0.8), ("RTN", 51.1, 82.5, 0.8),
        ("DOOR", 61, 82.5, 0.8), ("0V", 66.1, 82.5, 0.8),
        ("3V3", 77, 82.5, 0.8), ("DATA", 82.1, 82.5, 0.8),
        ("0V", 87.2, 82.5, 0.8),
        ("3V3", 102, 82.5, 0.8), ("DATA", 107.1, 82.5, 0.8),
        ("0V", 112.2, 82.5, 0.8),
        ("AUX CLOSED = ON", 100, 60.5, 1.0),
    ]
    for i, (text, x, y, size) in enumerate(labels):
        b.graphicItems.append(GrText(
            text=text, position=Position(X=x, Y=y), layer="F.SilkS",
            effects=Effects(font=Font(height=size, width=size,
                                      thickness=size * 0.15)),
            tstamp=uid("silk", i, text)))


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
                                         thermalBridgeWidth=0.5),
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
