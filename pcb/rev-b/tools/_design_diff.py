#!/usr/bin/env python3
"""Diff the KiCad board's footprint placements against design.py.

Reports which components were moved/rotated in KiCad relative to what design.py
generates (so the moves can be synced back into the source of truth), plus any
footprints present in one but not the other. Placements compared in board (page)
coordinates: design.C[ref]['at'] + page_origin.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from design import C, BOARD

OX, OY = BOARD["page_origin"]
PCB = os.path.join(os.path.dirname(__file__), "..", "sauna-rev-b.kicad_pcb")


def footprint_blocks(t, token="(footprint "):
    out, i = [], 0
    while True:
        i = t.find(token, i)
        if i < 0:
            break
        depth, j = 0, i
        while j < len(t):
            c = t[j]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(t[i:j + 1])
        i = j + 1
    return out


def main():
    t = open(PCB).read()
    actual = {}
    for b in footprint_blocks(t):
        mref = (re.search(r'\(property "Reference" "([^"]+)"', b) or
                re.search(r'\(fp_text\s+reference "([^"]+)"', b))
        mat = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b)
        if mref and mat:
            x, y = float(mat.group(1)), float(mat.group(2))
            rot = float(mat.group(3)) if mat.group(3) else 0.0
            actual[mref.group(1)] = (x, y, rot)

    moved = []
    for ref, comp in C.items():
        ex, ey, ea = comp["at"]
        exp = (round(ex + OX, 3), round(ey + OY, 3), ea % 360)
        if ref not in actual:
            print(f"  MISSING in board (in design.py): {ref}")
            continue
        ax, ay, aa = actual[ref]
        dpos = ((ax - exp[0]) ** 2 + (ay - exp[1]) ** 2) ** 0.5
        drot = (round(aa) - round(ea)) % 360
        if dpos > 0.02 or drot != 0:
            # board pos -> design raw literal (pre-TRIM)
            raw = (round(ax - OX + 2.0, 3), round(ay - OY + 5.0, 3))
            moved.append((ref, exp, (ax, ay, aa), dpos, raw))

    extra = sorted(set(actual) - set(C) - {"REF**"})
    print(f"\n{len(moved)} moved/rotated component(s):")
    for ref, exp, act, dpos, raw in sorted(moved, key=lambda m: -m[3]):
        print(f"  {ref:>8}: design(+page) {exp} -> board {act}  "
              f"(Δ{dpos:.2f}mm)  new raw literal at=({raw[0]}, {raw[1]}, "
              f"{int(act[2])})")
    if extra:
        print(f"\nfootprints in board but not design.py: {extra}")


if __name__ == "__main__":
    main()
