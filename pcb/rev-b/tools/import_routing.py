#!/usr/bin/env python3
"""Capture the hand-routed traces from sauna-rev-b.kicad_pcb into routing.py.

Once the board is being routed by hand in KiCad (more direct paths than the
maze autorouter found), KiCad becomes the routing source of truth. This reads
every copper segment + via out of the board, shifts them back to the design
origin (undoing BOARD['page_origin']), and writes routing.py -- exactly the
format generate_board.py / check_board.py consume. Run this instead of
autoroute.py after editing traces in KiCad.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from design import BOARD, NETS

PCB = os.path.join(os.path.dirname(__file__), "..", "sauna-rev-b.kicad_pcb")
OUT = os.path.join(os.path.dirname(__file__), "routing.py")
OX, OY = BOARD.get("page_origin", (0, 0))


def main():
    t = open(PCB).read()
    seg_re = re.compile(
        r'\(segment\s+\(start ([-\d.]+) ([-\d.]+)\)\s+\(end ([-\d.]+) ([-\d.]+)\)'
        r'\s+\(width ([-\d.]+)\)\s+\(layer "([^"]+)"\)\s+\(net "([^"]*)"\)')
    routes = []
    for m in seg_re.finditer(t):
        x1, y1, x2, y2, w, layer, net = m.groups()
        if net not in NETS or layer not in ("F.Cu", "B.Cu"):
            continue
        routes.append((net, layer, round(float(w), 3),
                       [(round(float(x1) - OX, 3), round(float(y1) - OY, 3)),
                        (round(float(x2) - OX, 3), round(float(y2) - OY, 3))]))

    vias = []
    for m in re.finditer(r'\(via\b(.*?)\(net "([^"]*)"\)', t, re.S):
        body, net = m.groups()
        if "(via" in body or net not in NETS:    # guard against block overrun
            continue
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)\)', body)
        if at:
            vias.append((net, (round(float(at.group(1)) - OX, 3),
                               round(float(at.group(2)) - OY, 3))))

    with open(OUT, "w") as f:
        f.write('"""CAPTURED from sauna-rev-b.kicad_pcb by import_routing.py.\n'
                'Hand-routed in KiCad -- re-run import_routing.py after trace '
                'edits.\nROUTES: (net, layer, width, [(x,y), ...]); '
                'VIAS: (net,(x,y))\n"""\n')
        f.write("ROUTES = [\n")
        for r in routes:
            f.write(f"    {r!r},\n")
        f.write("]\n\nVIAS = [\n")
        for v in vias:
            f.write(f"    {v!r},\n")
        f.write("]\n")
    print(f"captured {len(routes)} segments, {len(vias)} vias -> routing.py")


if __name__ == "__main__":
    main()
