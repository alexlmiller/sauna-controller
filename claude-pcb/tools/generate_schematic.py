#!/usr/bin/env python3
"""Generate claude-pcb/sauna-rev-b.kicad_sch from tools/design.py.

Style: every component is placed in a functional section and every pin gets a
global net label directly on its connection point. Unused pins get explicit
no-connect markers. All symbols are self-contained (embedded lib_symbols), so
the file opens with zero external library dependencies.
"""
import os
import sys
import uuid as uuidlib

sys.path.insert(0, os.path.dirname(__file__))
import design  # noqa: E402
from design import C, TITLE, REV  # noqa: E402

from kiutils.schematic import Schematic
from kiutils.symbol import Symbol, SymbolPin
from kiutils.items.common import (Position, Property, Effects, Font, Justify,
                                  TitleBlock, Stroke, ColorRGBA, PageSettings,
                                  Fill)
from kiutils.items.schitems import (SchematicSymbol, GlobalLabel, NoConnect,
                                    Text, SymbolInstance,
                                    HierarchicalSheetInstance)
from kiutils.items.syitems import SyRect

NS = uuidlib.UUID("9b1d6f6e-2f4a-4b1e-9a7e-5c3a1d2e4f60")


def uid(*parts):
    return str(uuidlib.uuid5(NS, "/".join(str(p) for p in parts)))


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


def main():
    out = os.path.join(os.path.dirname(__file__), "..", "sauna-rev-b.kicad_sch")
    sch = Schematic.create_new()
    sch.uuid = uid("sheet-root")
    sch.paper = PageSettings(paperSize="A3")
    sch.titleBlock = TitleBlock(
        title=f"{TITLE} - Rev {REV}", revision=REV,
        comments={1: "Generated from claude-pcb/tools/ - run ERC before use"})

    used_keys = sorted({c["symbol"] for c in C.values()})
    sch.libSymbols = [build_lib_symbol(k) for k in used_keys]

    section_texts = [
        (30, 25, "POWER INPUT + FUSING + 5V"),
        (118, 25, "COIL / SAFETY LOOP + OPTO INPUTS"),
        (200, 25, "LED OUTPUTS + MOSFETS"),
        (262, 25, "SENSORS / DOOR / PANEL"),
        (330, 25, "ESP32 DEVKITC SOCKET"),
        (415, 25, "TEST POINTS"),
        (14, 130, "INDICATORS"),
    ]
    for x, y, label in section_texts:
        sch.texts.append(Text(text=label, position=Position(X=x, Y=y, angle=0),
                              effects=effects(2.0), uuid=uid("txt", label)))

    for ref, comp in sorted(C.items()):
        spec = SYMBOLS[comp["symbol"]]
        sx, sy = comp["sch"]
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
        for fk, fv in comp.get("fields", {}).items():
            inst.properties.append(Property(
                key=fk, value=fv, id=nid,
                position=Position(X=sx, Y=sy, angle=0),
                effects=effects(1.27, hide=True)))
            nid += 1
        inst.pins = {num: uid("pin", ref, num) for num in spec["pins"]}
        sch.schematicSymbols.append(inst)

        # labels / no-connects at absolute pin positions (negate symbol Y)
        for num, (px, py, side) in spec["pins"].items():
            ax, ay = sx + px, sy - py
            net = comp["nets"].get(num)
            if net is None:
                sch.noConnects.append(NoConnect(
                    position=Position(X=ax, Y=ay), uuid=uid("nc", ref, num)))
                continue
            angle = 180 if side == "L" else 0
            just = "right" if side == "L" else "left"
            sch.globalLabels.append(GlobalLabel(
                text=net, shape="passive", fieldsAutoplaced=True,
                position=Position(X=ax, Y=ay, angle=angle),
                effects=effects(1.27, justify=just),
                uuid=uid("gl", ref, num)))

    sch.sheetInstances = [HierarchicalSheetInstance(instancePath="/", page="1")]
    sch.symbolInstances = [
        SymbolInstance(path=f"/{uid('sym', ref)}", reference=ref, unit=1,
                       value=C[ref]["value"],
                       footprint=f"sauna:{C[ref]['footprint']}")
        for ref in sorted(C)]

    sch.to_file(os.path.abspath(out))
    print(f"wrote {os.path.abspath(out)}: "
          f"{len(sch.schematicSymbols)} symbols, "
          f"{len(sch.globalLabels)} labels, {len(sch.noConnects)} NCs")

    # round-trip validation
    back = Schematic.from_file(os.path.abspath(out))
    assert len(back.schematicSymbols) == len(sch.schematicSymbols)
    print("round-trip parse OK")


if __name__ == "__main__":
    main()
