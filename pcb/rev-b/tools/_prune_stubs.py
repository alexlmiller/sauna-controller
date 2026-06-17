#!/usr/bin/env python3
"""Iteratively prune dead trace overhang (stubs) from routing.py.

A segment endpoint is a "dead leaf" if no pad, no via, and no other same-net
same-layer segment touches it. Such overhang is removed; if a via/pad/junction
sits in a segment's interior, the segment is shortened to that point instead of
deleted. Repeats until stable, so a multi-segment dead spur unravels back to the
first real anchor (pad / via / junction). GND-on-B.Cu is skipped (it bonds to
the pour). A dead leaf is never on an anchor-to-anchor path, so connectivity is
unaffected -- run check_board.py afterwards to confirm. Use --apply to rewrite.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import routing
from check_board import build_items, point_in_poly

OUT = os.path.join(os.path.dirname(__file__), "routing.py")
TOL, PAD_TOL, VIA_TOL = 0.06, 0.25, 0.45
EPS = 1e-6

PAD_C = []
for it in build_items():
    if it.kind == "pad" and it.net:
        cx = sum(p[0] for p in it.poly) / len(it.poly)
        cy = sum(p[1] for p in it.poly) / len(it.poly)
        PAD_C.append((it.net, frozenset(it.layers), (cx, cy), it.poly))
VIAS = [(n, (round(x, 3), round(y, 3))) for n, (x, y) in routing.VIAS]


def d(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def near_poly(p, poly, tol):
    if point_in_poly(p, poly):
        return True
    for i in range(len(poly)):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % len(poly)]
        px, py = p
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0 if L2 < EPS else max(0, min(1, ((px-ax)*dx+(py-ay)*dy)/L2))
        if math.hypot(px - (ax+t*dx), py - (ay+t*dy)) < tol:
            return True
    return False


def pad_anchor(p, net, layer):
    return any(n == net and layer in lay and near_poly(p, poly, PAD_TOL)
               for n, lay, c, poly in PAD_C)


def via_anchor(p, net):
    return any(n == net and d(p, v) < VIA_TOL for n, v in VIAS)


R = [[net, layer, w, tuple(map(float, pts[0])), tuple(map(float, pts[1]))]
     for net, layer, w, pts in routing.ROUTES]


def touches_other(E, idx, net, layer):
    for j, seg in enumerate(R):
        if seg is None or j == idx:
            continue
        n, l, w, a, b = seg
        if n != net or l != layer:
            continue
        if d(E, a) < TOL or d(E, b) < TOL:
            return True
        ax, ay = a
        bx, by = b
        px, py = E
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 < EPS:
            continue
        t = ((px - ax) * dx + (py - ay) * dy) / L2
        if EPS < t < 1 - EPS and \
           math.hypot(px - (ax+t*dx), py - (ay+t*dy)) < TOL:
            return True
    return False


def is_dead_leaf(E, idx, net, layer):
    return not (pad_anchor(E, net, layer) or via_anchor(E, net)
                or touches_other(E, idx, net, layer))


def nearest_cut(E, F, idx, net, layer):
    dx, dy = F[0] - E[0], F[1] - E[1]
    L2 = dx * dx + dy * dy
    if L2 < EPS:
        return None
    best = [None, 2.0]

    def consider(pt, tol):
        s = ((pt[0] - E[0]) * dx + (pt[1] - E[1]) * dy) / L2
        if s <= EPS or s >= 1 - EPS:
            return
        fx, fy = E[0] + s * dx, E[1] + s * dy
        if math.hypot(pt[0] - fx, pt[1] - fy) <= tol and s < best[1]:
            best[1] = s
            best[0] = (round(fx, 3), round(fy, 3))

    for n, v in VIAS:
        if n == net:
            consider(v, VIA_TOL)
    for j, seg in enumerate(R):
        if seg is None or j == idx:
            continue
        n, l, w, a, b = seg
        if n == net and l == layer:
            consider(a, TOL)
            consider(b, TOL)
    for n, lay, c, poly in PAD_C:
        if n == net and layer in lay:
            consider(c, PAD_TOL)
    return best[0]


removed, shortened = [], []
changed = True
while changed:
    changed = False
    for idx, seg in enumerate(R):
        if seg is None:
            continue
        net, layer, w, a, b = seg
        if net == "GND" and layer == "B.Cu":
            continue
        for E, F in ((a, b), (b, a)):
            if is_dead_leaf(E, idx, net, layer):
                cut = nearest_cut(E, F, idx, net, layer)
                if cut is None:
                    removed.append((net, layer, a, b))
                    R[idx] = None
                else:
                    shortened.append((net, layer, E, cut, F))
                    R[idx] = [net, layer, w, cut, F]
                changed = True
                break

print(f"removed {len(removed)} segment(s), shortened {len(shortened)}:")
for net, layer, a, b in removed:
    print(f"  - drop  {net:>10} {layer} {a}-{b}")
for net, layer, E, cut, F in shortened:
    print(f"  ~ short {net:>10} {layer} dead {E} -> cut at {cut} (keep ->{F})")

if "--apply" in sys.argv:
    out = [s for s in R if s is not None]
    with open(OUT, "w") as f:
        f.write('"""CAPTURED from sauna-rev-b.kicad_pcb by import_routing.py, '
                'dead stubs pruned by _prune_stubs.py.\nHand-routed in KiCad -- '
                're-run import_routing.py after trace edits (then _prune_stubs '
                'if needed).\nROUTES: (net, layer, width, [(x,y), ...]); '
                'VIAS: (net,(x,y))\n"""\n')
        f.write("ROUTES = [\n")
        for net, layer, w, a, b in out:
            f.write(f"    {(net, layer, w, [a, b])!r},\n")
        f.write("]\n\nVIAS = [\n")
        for v in routing.VIAS:
            f.write(f"    {v!r},\n")
        f.write("]\n")
    print(f"\napplied -> routing.py ({len(out)} routes, "
          f"{len(routing.VIAS)} vias)")
else:
    print("\n(dry run -- pass --apply to rewrite routing.py)")
