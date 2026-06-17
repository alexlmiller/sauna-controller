#!/usr/bin/env python3
"""Set the coil-drive power nets to their net-class width (1.0mm), flat.

COIL- / SRL250_RTN / +24V_SAFE were hand-routed at 0.2mm; design.NET_CLASSES
puts them in LED_OUT (1.0mm). Per request this widens every such segment to a
flat 1.0mm (no clearance-aware necking) -- tight spots get re-routed by hand.
Rewrites routing.py; run check_board after to see which spots to re-route.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import routing

OUT = os.path.join(os.path.dirname(__file__), "routing.py")
WIDEN = {"COIL-", "SRL250_RTN", "+24V_SAFE"}

out, changed = [], 0
for net, layer, w, pts in routing.ROUTES:
    if net in WIDEN and w < 1.0 - 1e-6:
        w = 1.0
        changed += 1
    out.append((net, layer, w, pts))

with open(OUT, "w") as f:
    f.write('"""CAPTURED from sauna-rev-b.kicad_pcb by import_routing.py; '
            'coil-drive nets set to net-class 1.0mm by _widen.py.\n'
            'Re-run import_routing.py after KiCad trace edits.\n'
            'ROUTES: (net, layer, width, [(x,y), ...]); VIAS: (net,(x,y))\n"""\n')
    f.write("ROUTES = [\n")
    for r in out:
        f.write(f"    {r!r},\n")
    f.write("]\n\nVIAS = [\n")
    for v in routing.VIAS:
        f.write(f"    {v!r},\n")
    f.write("]\n")
print(f"set {changed} segments to 1.0mm "
      f"(COIL- / SRL250_RTN / +24V_SAFE)")
