#!/usr/bin/env python3
"""Throwaway: find dangling trace endpoints (stubs) left after part removal.

A free endpoint = a segment end coincident with no pad, no via, and no other
same-net/same-layer trace. GND on B.Cu is excluded (it bonds to the pour, so a
"free" GND-on-plane end is absorbed by the ground plane, not a visible stub).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from check_board import build_items, point_in_poly


def near_poly(p, poly, tol):
    if point_in_poly(p, poly):
        return True
    for i in range(len(poly)):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % len(poly)]
        px, py = p
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0 if L2 < 1e-9 else max(0, min(1, ((px - ax) * dx +
                                               (py - ay) * dy) / L2))
        if math.hypot(px - (ax + t * dx), py - (ay + t * dy)) < tol:
            return True
    return False


def pt_seg(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 < 1e-9 else max(0, min(1, ((px - ax) * dx +
                                           (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


items = build_items()
pads = [it for it in items if it.kind == "pad" and it.net]
vias = [it for it in items if it.kind == "via"]
segs = [it for it in items if it.kind == "seg"]

stubs = []
for s in segs:
    for ep in s.seg:
        # GND on B.Cu bonds to the pour -> never a visible stub
        if s.net == "GND" and "B.Cu" in s.layers:
            continue
        if any(p.net == s.net and (s.layers & p.layers) and
               near_poly(ep, p.poly, 0.3) for p in pads):
            continue
        if any(v.net == s.net and near_poly(ep, v.poly, 0.45) for v in vias):
            continue
        if any(o is not s and o.net == s.net and (o.layers & s.layers) and
               pt_seg(ep, o.seg[0], o.seg[1]) < 0.1 for o in segs):
            continue
        stubs.append((s.net, round(ep[0], 2), round(ep[1], 2),
                      sorted(s.layers)))

# dedup identical points (a polyline vertex shared by 2 segs would show twice)
seen = set()
uniq = []
for st in stubs:
    key = (st[0], st[1], st[2])
    if key not in seen:
        seen.add(key)
        uniq.append(st)

print(f"{len(uniq)} dangling (non-GND-plane) trace endpoint(s)")
for net, x, y, lay in sorted(uniq):
    print(f"  {net:>10} at ({x:6.2f},{y:6.2f})  {lay}")
