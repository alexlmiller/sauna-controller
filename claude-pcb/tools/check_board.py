#!/usr/bin/env python3
"""Electrical + mechanical checks for the generated board.

Validates, from the same data the generator uses:
  1. courtyard overlaps / board boundary / antenna keepout violations
  2. copper clearance between items of different nets (per net class)
  3. full net connectivity (pads + segments + vias + B.Cu GND plane)

Exit code != 0 on any error. Run after every routing/placement edit.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import design
import routing
from design import C, NETS, NET_CLASSES, BOARD
from footprints import FOOTPRINTS, MOUNTING_HOLE

EPS = 1e-6


def rot(px, py, angle):
    a = math.radians(angle)
    return (px * math.cos(a) + py * math.sin(a),
            -px * math.sin(a) + py * math.cos(a))


def pad_polygon(cx, cy, sx, sy, angle):
    pts = [(-sx / 2, -sy / 2), (sx / 2, -sy / 2),
           (sx / 2, sy / 2), (-sx / 2, sy / 2)]
    return [(cx + rot(px, py, angle)[0], cy + rot(px, py, angle)[1])
            for px, py in pts]


def seg_seg_dist(p1, p2, p3, p4):
    def seg_pt(a, b, p):
        ax, ay = a; bx, by = b; px, py = p
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 < EPS:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

    d1, d2 = ccw(p3, p4, p1), ccw(p3, p4, p2)
    d3, d4 = ccw(p1, p2, p3), ccw(p1, p2, p4)
    if ((d1 > 0) != (d2 > 0) or abs(d1) < EPS or abs(d2) < EPS) and \
       ((d3 > 0) != (d4 > 0) or abs(d3) < EPS or abs(d4) < EPS):
        # conservative possible-intersection -> verify by min endpoint dist
        if (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0):
            return 0.0
    return min(seg_pt(p1, p2, p3), seg_pt(p1, p2, p4),
               seg_pt(p3, p4, p1), seg_pt(p3, p4, p2))


def point_in_poly(p, poly):
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xt = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < xt:
                inside = not inside
    return inside


def poly_seg_dist(poly, a, b):
    if point_in_poly(a, poly) or point_in_poly(b, poly):
        return 0.0
    d = min(seg_seg_dist(poly[i], poly[(i + 1) % len(poly)], a, b)
            for i in range(len(poly)))
    return d


def poly_poly_dist(pa, pb):
    if any(point_in_poly(p, pb) for p in pa) or \
       any(point_in_poly(p, pa) for p in pb):
        return 0.0
    return min(seg_seg_dist(pa[i], pa[(i + 1) % len(pa)],
                            pb[j], pb[(j + 1) % len(pb)])
               for i in range(len(pa)) for j in range(len(pb)))


def clearance_of(net):
    return NET_CLASSES[NETS[net]]["clearance"] if net in NETS else 0.2


class Item:
    """A copper item: pad, segment or via."""

    def __init__(self, kind, net, layers, label, poly=None, seg=None,
                 width=0.0):
        self.kind, self.net, self.layers = kind, net, set(layers)
        self.label, self.poly, self.seg, self.width = label, poly, seg, width

    def dist(self, other):
        if self.poly is not None and other.poly is not None:
            return poly_poly_dist(self.poly, other.poly)
        if self.poly is not None and other.seg is not None:
            return poly_seg_dist(self.poly, *other.seg) - other.width / 2
        if self.seg is not None and other.poly is not None:
            return poly_seg_dist(other.poly, *self.seg) - self.width / 2
        return seg_seg_dist(*self.seg, *other.seg) - \
            self.width / 2 - other.width / 2


def build_items():
    items = []
    for ref in sorted(C):
        comp = C[ref]
        x, y, ang = comp["at"]
        for pad in FOOTPRINTS[comp["footprint"]]["pads"]:
            num, ptype, shape, (px, py), (sx, sy), drill = pad
            dx, dy = rot(px, py, ang)
            poly = pad_polygon(x + dx, y + dy, sx, sy, ang)
            layers = {"F.Cu"} if ptype == "smd" else {"F.Cu", "B.Cu"}
            net = comp["nets"].get(num)
            items.append(Item("pad", net, layers, f"{ref}.{num}", poly=poly))
    for i, (x, y) in enumerate(BOARD["mounting_holes"], start=1):
        d = MOUNTING_HOLE["drill"]
        items.append(Item("hole", None, {"F.Cu", "B.Cu"}, f"H{i}",
                          poly=pad_polygon(x, y, d, d, 0)))
    for i, (net, layer, width, pts) in enumerate(routing.ROUTES):
        assert net in NETS, f"route {i}: unknown net {net}"
        for j in range(len(pts) - 1):
            items.append(Item("seg", net, {layer},
                              f"route[{i}]{net}/{j}",
                              seg=(pts[j], pts[j + 1]), width=width))
    for i, (net, (x, y)) in enumerate(routing.VIAS):
        items.append(Item("via", net, {"F.Cu", "B.Cu"}, f"via[{i}]{net}",
                          poly=pad_polygon(x, y, 0.8, 0.8, 0)))
    return items


def check_courtyards():
    errs = []
    boxes = {}
    for ref in sorted(C):
        comp = C[ref]
        x, y, ang = comp["at"]
        x1, y1, x2, y2 = FOOTPRINTS[comp["footprint"]]["courtyard"]
        corners = [rot(px, py, ang) for px, py in
                   [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]]
        xs = [x + c[0] for c in corners]
        ys = [y + c[1] for c in corners]
        boxes[ref] = (min(xs), min(ys), max(xs), max(ys))
    for i, (x, y) in enumerate(BOARD["mounting_holes"], start=1):
        r = MOUNTING_HOLE["pad"] / 2
        boxes[f"H{i}"] = (x - r, y - r, x + r, y + r)
    refs = sorted(boxes)
    for i, a in enumerate(refs):
        ax1, ay1, ax2, ay2 = boxes[a]
        # board boundary
        if ax1 < -0.01 or ay1 < -0.01 or ax2 > BOARD["width"] + 0.01 or \
           ay2 > BOARD["height"] + 0.01:
            errs.append(f"BOUNDARY: {a} courtyard {boxes[a]} off board")
        # antenna keepout (only parts; H1..H4 exempt by position anyway)
        kx1, ky1, kx2, ky2 = BOARD["antenna_keepout"]
        if not (ax2 <= kx1 or ax1 >= kx2 or ay2 <= ky1 or ay1 >= ky2):
            errs.append(f"KEEPOUT: {a} courtyard intrudes antenna zone")
        for b in refs[i + 1:]:
            bx1, by1, bx2, by2 = boxes[b]
            if not (ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1):
                ov = min(ax2 - bx1, bx2 - ax1, ay2 - by1, by2 - ay1)
                errs.append(f"OVERLAP: {a} x {b} (by {ov:.2f}mm)")
    return errs


def check_clearance(items):
    errs = []
    n = len(items)
    for i in range(n):
        a = items[i]
        for j in range(i + 1, n):
            b = items[j]
            if a.net == b.net and a.net is not None:
                continue
            if not (a.layers & b.layers):
                continue
            # same-footprint NC pads sit close together legitimately
            if a.kind == "pad" and b.kind == "pad" and \
               a.label.split(".")[0] == b.label.split(".")[0]:
                req = 0.13
            else:
                req = max(clearance_of(a.net) if a.net else 0.2,
                          clearance_of(b.net) if b.net else 0.2)
            d = a.dist(b)
            if d < req - 0.001:
                errs.append(f"CLEARANCE {d:.3f} < {req}: "
                            f"{a.label}({a.net}) vs {b.label}({b.net})")
    return errs


def check_keepout_copper(items):
    kx1, ky1, kx2, ky2 = BOARD["antenna_keepout"]
    keep = [(kx1, ky1), (kx2, ky1), (kx2, ky2), (kx1, ky2)]
    errs = []
    for it in items:
        if it.net is None:
            continue
        if it.poly is not None:
            d = poly_poly_dist(keep, it.poly)
        else:
            d = poly_seg_dist(keep, *it.seg) - it.width / 2
        if d < 0.25:
            errs.append(f"ANTENNA: copper {it.label}({it.net}) in keepout")
    return errs


def check_connectivity(items):
    errs = []
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent.setdefault(x, x)
        parent.setdefault(y, y)
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    by_net = {}
    for it in items:
        if it.net:
            by_net.setdefault(it.net, []).append(it)
            parent[id(it)] = id(it)

    for net, group in by_net.items():
        # GND plane joins everything with B.Cu presence
        if net == "GND":
            plane = "B_PLANE"
            parent.setdefault(plane, plane)
            for it in group:
                if "B.Cu" in it.layers:
                    union(id(it), plane)
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if not (a.layers & b.layers):
                    continue
                if a.dist(b) <= 0.001:
                    union(id(a), id(b))

    for net, group in sorted(by_net.items()):
        roots = {}
        for it in group:
            roots.setdefault(find(id(it)), []).append(it.label)
        if len(roots) > 1:
            parts = sorted(roots.values(), key=len, reverse=True)
            detail = " | ".join(",".join(sorted(p)) for p in parts)
            errs.append(f"OPEN NET {net}: {len(roots)} islands: {detail}")
    return errs


def main():
    verbose = "-v" in sys.argv
    errs = check_courtyards()
    items = build_items()
    errs += check_keepout_copper(items)
    errs += check_clearance(items)
    conn = check_connectivity(items)
    if "--no-conn" not in sys.argv:
        errs += conn
    if errs:
        for e in errs[:80]:
            print("ERROR:", e)
        if len(errs) > 80:
            print(f"... and {len(errs) - 80} more")
        print(f"\n{len(errs)} errors")
        sys.exit(1)
    print(f"all checks passed ({len(items)} copper items, "
          f"{len(routing.ROUTES)} routes, {len(routing.VIAS)} vias)")


if __name__ == "__main__":
    main()
