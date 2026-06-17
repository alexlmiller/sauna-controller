#!/usr/bin/env python3
"""Generate pcb/rev-b/sauna-rev-b.kicad_sch from tools/design.py.

Style: components are grouped into readable functional blocks, each connected
pin gets a short visible wire stub and a local net label, and important field
wiring behavior is documented with notes. Unused pins get explicit no-connect
markers. All symbols are self-contained (embedded lib_symbols), so the file
opens with zero external library dependencies.
"""
import os
import sys
import uuid as uuidlib

sys.path.insert(0, os.path.dirname(__file__))
import design  # noqa: E402
from design import C, TITLE, REV  # noqa: E402
from generate_bom import lcsc_for  # noqa: E402  (LCSC part # per footprint+value)

from kiutils.schematic import Schematic
from kiutils.symbol import Symbol, SymbolPin
from kiutils.items.common import (Position, Property, Effects, Font, Justify,
                                  TitleBlock, Stroke, ColorRGBA, PageSettings,
                                  Fill)
from kiutils.items.schitems import (SchematicSymbol, Connection, LocalLabel,
                                    NoConnect, Text, Rectangle, TextBox,
                                    SymbolInstance,
                                    HierarchicalSheetInstance)
from kiutils.items.syitems import SyRect

NS = uuidlib.UUID("9b1d6f6e-2f4a-4b1e-9a7e-5c3a1d2e4f60")
GRID = 1.27
STUB_LENGTH = 3.81


def uid(*parts):
    return str(uuidlib.uuid5(NS, "/".join(str(p) for p in parts)))


def snap(v):
    return round(round(v / GRID) * GRID, 3)


def effects(h=1.27, hide=False, justify=None):
    e = Effects(font=Font(height=h, width=h), hide=hide)
    if justify:
        e.justify = Justify(horizontally=justify)
    return e


# ---------------------------------------------------------------------------
# Symbol library: key -> dict(ref_prefix, pins {num: (px, py, side)}, body)
# Symbol space is Y-UP (KiCad library convention); placement negates Y.
# side: 'L' label points left, 'R' label points right.
# ---------------------------------------------------------------------------
def two_pin(prefix):
    return dict(ref=prefix,
                pins={"1": (-5.08, 0.0, "L"), "2": (5.08, 0.0, "R")},
                body=(-2.54, -1.27, 2.54, 1.27))


SYMBOLS = {
    "R": two_pin("R"), "C": two_pin("C"), "CP": two_pin("C"),
    "D": two_pin("D"), "TVS": two_pin("D"), "ESD": two_pin("D"),
    "LED": two_pin("D"), "FUSE": two_pin("F"), "POLYFUSE": two_pin("F"),
    "TP": dict(ref="TP", pins={"1": (-5.08, 0.0, "L")},
               body=(-2.54, -1.27, 0, 1.27)),
    "NMOS": dict(ref="Q", pins={"1": (-7.62, 0.0, "L"),
                                "2": (7.62, 2.54, "R"),
                                "3": (7.62, -2.54, "R")},
                 body=(-5.08, -5.08, 5.08, 5.08)),
    "OPTO": dict(ref="U", pins={"1": (-7.62, 2.54, "L"),
                                "2": (-7.62, -2.54, "L"),
                                "3": (7.62, -2.54, "R"),
                                "4": (7.62, 2.54, "R")},
                 body=(-5.08, -5.08, 5.08, 5.08)),
    "USBLC6": dict(ref="U", pins={"1": (-7.62, 2.54, "L"),
                                  "2": (-7.62, 0.0, "L"),
                                  "3": (-7.62, -2.54, "L"),
                                  "4": (7.62, -2.54, "R"),
                                  "5": (7.62, 0.0, "R"),
                                  "6": (7.62, 2.54, "R")},
                  body=(-5.08, -5.08, 5.08, 5.08)),
    "REG3": dict(ref="U", pins={"1": (-7.62, 2.54, "L"),
                                "2": (-7.62, -2.54, "L"),
                                "3": (7.62, 2.54, "R")},
                 body=(-5.08, -5.08, 5.08, 5.08)),
}
for n in (2, 3, 4, 5):
    SYMBOLS[f"CONN{n}"] = dict(
        ref="J",
        pins={str(k + 1): (-7.62, -(2.54 * k), "L") for k in range(n)},
        body=(-5.08, -(2.54 * (n - 1)) - 2.54, 0, 2.54))
SYMBOLS["CONN19"] = dict(
    ref="J",
    pins={str(k + 1): (-7.62, -(2.54 * k), "L") for k in range(19)},
    body=(-5.08, -(2.54 * 18) - 2.54, 0, 2.54))

PIN_NAMES = {
    "NMOS": {"1": "G", "2": "D", "3": "S"},
    "OPTO": {"1": "A", "2": "K", "3": "E", "4": "C"},
    "USBLC6": {"1": "IO1", "2": "GND", "3": "IO2",
               "4": "IO2b", "5": "VBUS", "6": "IO1b"},
    "REG3": {"1": "VIN", "2": "GND", "3": "VOUT"},
}


def build_lib_symbol(key):
    spec = SYMBOLS[key]
    name = f"sauna:{key}"
    sym = Symbol.create_new(id=name, reference=spec["ref"], value=key)
    sym.pinNames = True
    sym.pinNamesOffset = 0.508
    # body unit (common graphics)
    body = Symbol(libraryNickname=None, entryName=f"{key}_0_1")
    x1, y1, x2, y2 = spec["body"]
    body.graphicItems.append(SyRect(
        start=Position(X=x1, Y=y1), end=Position(X=x2, Y=y2),
        stroke=Stroke(width=0.254, type="default",
                      color=ColorRGBA(0, 0, 0, 0)), fill=Fill(type="background")))
    # pin unit
    pu = Symbol(libraryNickname=None, entryName=f"{key}_1_1")
    names = PIN_NAMES.get(key, {})
    for num, (px, py, side) in spec["pins"].items():
        angle = 0 if side == "L" else 180
        length = abs(px) - (abs(spec["body"][0]) if side == "L"
                            else abs(spec["body"][2]))
        pin = SymbolPin(electricalType="passive", graphicalStyle="line",
                        position=Position(X=px, Y=py, angle=angle),
                        length=max(length, 2.54),
                        name=names.get(num, "~"), number=num)
        pin.nameEffects = effects(1.0)
        pin.numberEffects = effects(1.0)
        pu.pins.append(pin)
    sym.units = [body, pu]
    return sym


# A2 readable schematic floorplan. These are schematic-only positions; the PCB
# placement remains in design.py's "at" field.
SCHEMATIC_POS = {
    # Power input, protection, conversion, and rail indicators.
    "J_PWR": (30, 45), "D1": (28, 75), "C4": (52, 75), "C5": (76, 75),
    "F1": (35, 108), "F2": (35, 123), "F3": (35, 138), "F4": (35, 153),
    "U1": (88, 138), "C1": (120, 118), "C2": (120, 138),
    "C3": (120, 153),
    "R25": (28, 182), "LED1": (50, 182),
    "R26": (28, 197), "LED2": (50, 197),
    "R27": (28, 212), "LED3": (50, 212),
    "PF1": (82, 182), "TP2": (112, 182), "TP3": (112, 197),
    "C8": (132, 197),

    # Coil, high-temp safety loop, high-temp opto, relay monitor, AUX output.
    "J_SRL250": (178, 45), "J_COIL": (178, 75),
    "D5": (214, 78), "R7": (244, 55), "R12": (244, 70), "Q1": (274, 78),
    "R2": (214, 118), "D3": (214, 138), "D10": (238, 138),
    "OPT2": (274, 124), "R5": (310, 118),
    "J_RELAY_FB": (350, 45), "R1": (386, 45), "D2": (386, 65),
    "D9": (410, 65), "OPT_RELAY_FB": (444, 50), "R4": (480, 45),
    "J_AUX_OUT": (350, 102), "D11": (386, 104), "R32": (410, 126),
    "R33": (452, 126), "Q6": (444, 112),

    # LED strip switching.
    "J_LED": (170, 245), "C6": (170, 292), "C7": (170, 308),
    "R8": (220, 212), "Q2": (245, 225), "R13": (268, 212),
    "R28": (220, 262), "LED4": (245, 262),
    "R9": (300, 212), "Q3": (325, 225), "R14": (348, 212),
    "R29": (300, 262), "LED5": (325, 262),
    "R10": (380, 212), "Q4": (405, 225), "R15": (428, 212),
    "R30": (380, 262), "LED6": (405, 262),
    "R11": (460, 212), "Q5": (485, 225), "R16": (508, 212),
    "R31": (460, 262), "LED7": (485, 262),

    # Field inputs, sensors, and panel UART/power.
    "J_PANEL": (30, 260), "R23": (74, 260), "R24": (74, 278),
    "U2": (118, 270), "C10": (88, 298),
    "J_DOOR": (30, 322), "D6": (74, 322), "R18": (100, 322),
    "C9": (124, 322), "R17": (148, 322),
    "J_BENCH": (30, 362), "R19": (74, 358), "R21": (100, 362),
    "D7": (128, 362),
    "J_CEILING": (30, 392), "R20": (74, 388), "R22": (100, 392),
    "D8": (128, 392),

    # ESP32 DevKitC socket.
    "J_ESP2": (430, 322), "J_ESP1": (510, 322),
}

SECTION_BOXES = [
    (10, 20, 150, 225, "POWER INPUT, PTC PROTECTION, 5V, STATUS"),
    (160, 20, 325, 155, "COIL + HIGH TEMP SAFETY LOOP"),
    (335, 20, 505, 155, "RELAY MONITOR + AUX OUTPUT"),
    (160, 180, 525, 280, "RGBW LED LOW-SIDE OUTPUTS"),
    (10, 235, 150, 405, "PANEL, DOOR, DS18B20 SENSOR INPUTS"),
    (415, 300, 570, 405, "ESP32 DEVKITC V4 SOCKET"),
]

NOTES = [
    (163, 147, 155, 17,
     "High-temp loop: +24V_SAFE leaves J_SRL250 OUT, returns as "
     "SRL250_RTN, then feeds COIL+ on J_COIL. GPIO35 senses SRL250_RTN."),
    (338, 143, 160, 14,
     "Relay monitor uses a 24 V wetting loop through the contactor 13/14 "
     "aux contact. Opto output pulls GPIO34 low when active."),
    (338, 126, 160, 12,
     "AUX output is a protected 24 V low-side switch on GPIO4. Leave GPIO4 "
     "unconfigured if unused."),
    (418, 392, 145, 11,
     "Use Espressif ESP32-DevKitC V4 with WROOM-32E/32D. Do not use WROVER: "
     "Rev B uses GPIO16/GPIO17."),
    (14, 398, 132, 10,
     "Panel is direct 3.3 V UART over the short Cat5e run: controller "
     "GPIO32 TX / GPIO33 RX."),
]


def stroke(width=0.152):
    return Stroke(width=width, type="default", color=ColorRGBA(0, 0, 0, 0))


def main():
    out = os.path.join(os.path.dirname(__file__), "..", "sauna-rev-b.kicad_sch")
    sch = Schematic.create_new()
    sch.uuid = uid("sheet-root")
    sch.paper = PageSettings(paperSize="A2")
    sch.titleBlock = TitleBlock(
        title=f"{TITLE} - Rev {REV}", revision=REV,
        comments={1: "Generated from pcb/rev-b/tools/ - run ERC before use",
                  2: "Same-name local labels connect within this sheet"})

    used_keys = sorted({c["symbol"] for c in C.values()})
    sch.libSymbols = [build_lib_symbol(k) for k in used_keys]

    for x1, y1, x2, y2, label in SECTION_BOXES:
        sch.shapes.append(Rectangle(
            start=Position(X=x1, Y=y1), end=Position(X=x2, Y=y2),
            stroke=stroke(0.22), fill=Fill(type="none"),
            uuid=uid("box", label)))
        sch.texts.append(Text(
            text=label, position=Position(X=x1 + 3, Y=y1 + 5, angle=0),
            effects=effects(2.0), uuid=uid("txt", label)))

    sch.texts.append(Text(
        text="Readable functional schematic. Net names are authoritative; "
             "PCB placement is generated separately from design.py.",
        position=Position(X=10, Y=12, angle=0), effects=effects(1.4),
        uuid=uid("txt", "schematic-note")))

    for x, y, w, h, text in NOTES:
        sch.textBoxes.append(TextBox(
            text=text, position=Position(X=x, Y=y, angle=0),
            size=Position(X=w, Y=h), stroke=stroke(0.12),
            fill=Fill(type="none"), effects=effects(1.05),
            uuid=uid("note", text[:30])))

    def add_wire(points, key):
        sch.graphicalItems.append(Connection(
            type="wire",
            points=[Position(X=round(x, 3), Y=round(y, 3))
                    for x, y in points],
            stroke=stroke(0.152), uuid=uid("wire", key)))

    def add_pin_label(ref, num, spec, net, pos):
        px, py, side = spec["pins"][num]
        ax, ay = pos[0] + px, pos[1] - py
        direction = -1 if side == "L" else 1
        lx = ax + direction * STUB_LENGTH
        ly = ay
        add_wire([(ax, ay), (lx, ly)], ("stub", ref, num))
        angle = 180 if side == "L" else 0
        just = "right" if side == "L" else "left"
        sch.labels.append(LocalLabel(
            text=net, position=Position(X=round(lx, 3), Y=round(ly, 3),
                                        angle=angle),
            effects=effects(1.12, justify=just),
            uuid=uid("label", ref, num, net)))

    for ref, comp in sorted(C.items()):
        spec = SYMBOLS[comp["symbol"]]
        sx, sy = SCHEMATIC_POS.get(ref, comp["sch"])
        sx, sy = snap(sx), snap(sy)
        su = uid("sym", ref)
        inst = SchematicSymbol(
            libraryNickname="sauna", entryName=comp["symbol"],
            libName=None,
            position=Position(X=sx, Y=sy, angle=0),
            unit=1, inBom=True, onBoard=True, uuid=su)
        inst.properties = [
            Property(key="Reference", value=ref, id=0,
                     position=Position(X=sx, Y=sy - 7.62, angle=0),
                     effects=effects(1.27)),
            Property(key="Value", value=comp["value"], id=1,
                     position=Position(X=sx, Y=sy + 7.62 +
                                       (2.54 * len(spec["pins"]) if
                                        comp["symbol"].startswith("CONN")
                                        else 0), angle=0),
                     effects=effects(1.27)),
            Property(key="Footprint", value=f"sauna:{comp['footprint']}",
                     id=2, position=Position(X=sx, Y=sy, angle=0),
                     effects=effects(1.27, hide=True)),
            Property(key="Datasheet", value="", id=3,
                     position=Position(X=sx, Y=sy, angle=0),
                     effects=effects(1.27, hide=True)),
        ]
        nid = 4
        lcsc = lcsc_for(comp["footprint"], comp["value"])  # JLC/LCSC part #
        if lcsc:
            inst.properties.append(Property(
                key="LCSC", value=lcsc, id=nid,
                position=Position(X=sx, Y=sy, angle=0),
                effects=effects(1.27, hide=True)))
            nid += 1
        for fk, fv in comp.get("fields", {}).items():
            inst.properties.append(Property(
                key=fk, value=fv, id=nid,
                position=Position(X=sx, Y=sy, angle=0),
                effects=effects(1.27, hide=True)))
            nid += 1
        inst.pins = {num: uid("pin", ref, num) for num in spec["pins"]}
        sch.schematicSymbols.append(inst)

        # Wire stubs + local labels at absolute pin positions (negate symbol Y).
        # Local labels keep the netlist exact without turning the page into one
        # giant crossing wire maze; the section placement and notes make the
        # electrical function readable.
        for num, (px, py, side) in spec["pins"].items():
            ax, ay = sx + px, sy - py
            net = comp["nets"].get(num)
            if net is None:
                sch.noConnects.append(NoConnect(
                    position=Position(X=ax, Y=ay), uuid=uid("nc", ref, num)))
                continue
            add_pin_label(ref, num, spec, net, (sx, sy))

    sch.sheetInstances = [HierarchicalSheetInstance(instancePath="/", page="1")]
    sch.symbolInstances = [
        SymbolInstance(path=f"/{uid('sym', ref)}", reference=ref, unit=1,
                       value=C[ref]["value"],
                       footprint=f"sauna:{C[ref]['footprint']}")
        for ref in sorted(C)]

    sch.to_file(os.path.abspath(out))
    print(f"wrote {os.path.abspath(out)}: "
          f"{len(sch.schematicSymbols)} symbols, "
          f"{len(sch.labels)} labels, {len(sch.noConnects)} NCs, "
          f"{len(sch.graphicalItems)} wires")

    # round-trip validation
    back = Schematic.from_file(os.path.abspath(out))
    assert len(back.schematicSymbols) == len(sch.schematicSymbols)
    print("round-trip parse OK")


if __name__ == "__main__":
    main()
