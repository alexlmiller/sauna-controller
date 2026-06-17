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


def circle_poly(cx, cy, r, n=16):
    """N-gon approximating a round pad/via (KiCad models these as circles, so a
    square over-estimates corner-to-corner clearance for diagonal neighbours)."""
    return [(cx + r * math.cos(2 * math.pi * k / n),
             cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


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
                          poly=circle_poly(x, y, 0.4)))
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


EDGE_CLEAR = 0.3       # min copper-to-board-edge clearance (matches DRC rule)


def edge_intrusion(x, y, half):
    """mm a copper point (+ half width) intrudes past the board edge or a
    rounded corner arc; None if clear. Mirrors KiCad copper_edge_clearance."""
    W, H, r = BOARD["width"], BOARD["height"], BOARD["corner_radius"]
    for ccx, ccy, sx, sy in ((r, r, -1, -1), (W - r, r, 1, -1),
                             (r, H - r, -1, 1), (W - r, H - r, 1, 1)):
        in_quad = (x < ccx if sx < 0 else x > ccx) and \
                  (y < ccy if sy < 0 else y > ccy)
        if in_quad:
            slack = (r - EDGE_CLEAR) - (math.hypot(x - ccx, y - ccy) + half)
            return -slack if slack < -EPS else None
    m = min(x, W - x, y, H - y) - half - EDGE_CLEAR
    return -m if m < -EPS else None


def check_edge_clearance(items):
    errs = []
    for it in items:
        if it.kind == "hole":
            continue                       # holes are themselves edge cuts
        if it.poly is not None:
            pts = [(p[0], p[1], 0.0) for p in it.poly]
        else:
            (x1, y1), (x2, y2) = it.seg
            n = max(1, int(math.hypot(x2 - x1, y2 - y1) / 0.25))
            pts = [(x1 + (x2 - x1) * t / n, y1 + (y2 - y1) * t / n,
                    it.width / 2) for t in range(n + 1)]
        for x, y, half in pts:
            d = edge_intrusion(x, y, half)
            if d is not None:
                errs.append(f"EDGE CLEARANCE {EDGE_CLEAR - d:.3f} < "
                            f"{EDGE_CLEAR}: {it.label}({it.net}) at "
                            f"({x:.1f},{y:.1f})")
                break
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


PLANE_G = 0.2          # B.Cu pour flood-fill resolution (mm)
ZONE_INSET = 0.6       # GND zone outline inset (matches generate_board.py)


def plane_components(items):
    """Flood-fill the B.Cu GND pour into connected islands.

    Models KiCad's zone fill: starts from the inset board outline, removes the
    antenna keepout, and carves a void (clearance + half track width) around
    every *non-GND* B.Cu copper item. GND items are pour contacts, not voids.

    Returns (comp, nx, ny): comp[j*nx+i] is the island id at that cell, 0 = no
    copper. Two GND pads/vias are plane-connected only if they touch the same
    island -- which is exactly the test KiCad's connectivity engine applies.
    """
    from collections import deque
    W, H, G = BOARD["width"], BOARD["height"], PLANE_G
    nx, ny = int(W / G) + 1, int(H / G) + 1
    allowed = bytearray(nx * ny)
    for j in range(ny):
        if ZONE_INSET <= j * G <= H - ZONE_INSET:
            row = j * nx
            for i in range(nx):
                if ZONE_INSET <= i * G <= W - ZONE_INSET:
                    allowed[row + i] = 1

    def carve_rect(x1, y1, x2, y2):
        i1, i2 = max(0, int(x1 / G)), min(nx - 1, int(math.ceil(x2 / G)))
        j1, j2 = max(0, int(y1 / G)), min(ny - 1, int(math.ceil(y2 / G)))
        for j in range(j1, j2 + 1):
            row = j * nx
            for i in range(i1, i2 + 1):
                allowed[row + i] = 0

    def carve_seg(a, b, rad):
        (ax, ay), (bx, by) = a, b
        i1 = max(0, int((min(ax, bx) - rad) / G))
        i2 = min(nx - 1, int(math.ceil((max(ax, bx) + rad) / G)))
        j1 = max(0, int((min(ay, by) - rad) / G))
        j2 = min(ny - 1, int(math.ceil((max(ay, by) + rad) / G)))
        dx, dy = bx - ax, by - ay
        L2, r2 = dx * dx + dy * dy, rad * rad
        for j in range(j1, j2 + 1):
            py, row = j * G, j * nx
            for i in range(i1, i2 + 1):
                px = i * G
                if L2 < EPS:
                    d2 = (px - ax) ** 2 + (py - ay) ** 2
                else:
                    t = max(0.0, min(1.0, ((px - ax) * dx +
                                           (py - ay) * dy) / L2))
                    d2 = (px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2
                if d2 < r2:
                    allowed[row + i] = 0

    gcl = clearance_of("GND")
    kx1, ky1, kx2, ky2 = BOARD["antenna_keepout"]
    carve_rect(kx1 - gcl, ky1 - gcl, kx2 + gcl, ky2 + gcl)
    for it in items:
        if it.net == "GND" or "B.Cu" not in it.layers:
            continue
        cl = max(gcl, clearance_of(it.net) if it.net else 0.2)
        if it.poly is not None:
            xs = [p[0] for p in it.poly]
            ys = [p[1] for p in it.poly]
            carve_rect(min(xs) - cl, min(ys) - cl, max(xs) + cl, max(ys) + cl)
        else:
            carve_seg(it.seg[0], it.seg[1], it.width / 2 + cl)

    comp = [0] * (nx * ny)
    cid = 0
    for s in range(nx * ny):
        if allowed[s] and not comp[s]:
            cid += 1
            comp[s] = cid
            q = deque([s])
            while q:
                c = q.popleft()
                cx = c % nx
                if cx + 1 < nx and allowed[c + 1] and not comp[c + 1]:
                    comp[c + 1] = cid
                    q.append(c + 1)
                if cx and allowed[c - 1] and not comp[c - 1]:
                    comp[c - 1] = cid
                    q.append(c - 1)
                if c + nx < nx * ny and allowed[c + nx] and not comp[c + nx]:
                    comp[c + nx] = cid
                    q.append(c + nx)
                if c - nx >= 0 and allowed[c - nx] and not comp[c - nx]:
                    comp[c - nx] = cid
                    q.append(c - nx)
    return comp, nx, ny


def plane_contacts(comp, nx, ny, poly):
    """Islands a GND pad/via bonds to: any pour cell within a thermal-relief
    reach (item radius + thermalGap) of its centre."""
    G = PLANE_G
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    rad = max(math.hypot(x - cx, y - cy) for x, y in poly) + 0.6
    i0, j0, rr, r2 = int(cx / G), int(cy / G), int(rad / G) + 1, rad * rad
    found = set()
    for j in range(max(0, j0 - rr), min(ny, j0 + rr + 1)):
        for i in range(max(0, i0 - rr), min(nx, i0 + rr + 1)):
            c = comp[j * nx + i]
            if c and (i * G - cx) ** 2 + (j * G - cy) ** 2 <= r2:
                found.add(c)
    return found


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

    plane_islands = 0
    live_islands = set()
    for net, group in by_net.items():
        # GND items bond to the B.Cu pour only where filled copper actually
        # reaches them, and two items share GND only if they sit on the same
        # pour island. A fragmented plane therefore shows up as open GND.
        if net == "GND":
            comp, nx, ny = plane_components(items)
            plane_islands = len({c for c in comp if c})
            for it in group:
                if "B.Cu" not in it.layers:
                    continue        # F.Cu-only: bonds via adjacency below
                polys = [it.poly] if it.poly is not None else \
                    [pad_polygon(it.seg[0][0], it.seg[0][1], 0.2, 0.2, 0),
                     pad_polygon(it.seg[1][0], it.seg[1][1], 0.2, 0.2, 0)]
                for poly in polys:
                    for cid in plane_contacts(comp, nx, ny, poly):
                        live_islands.add(cid)
                        node = ("PLANE", cid)
                        parent.setdefault(node, node)
                        union(id(it), node)
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if not (a.layers & b.layers):
                    continue
                if a.dist(b) <= 0.001:
                    union(id(a), id(b))

    # Pour islands that carry no GND copper are dead slivers -- harmless, and
    # KiCad deletes them when the zone removes isolated islands. Only GND
    # *items* stranded onto a separate island matter, and that is reported as
    # an open GND net below.
    dead = plane_islands - len(live_islands)
    if dead > 0:
        print(f"note: {dead} dead B.Cu pour sliver(s) carry no GND copper "
              f"(KiCad removes these via zone island-removal)")
    # Multiple *live* islands are fine if a shared pad or an F.Cu GND bridge
    # ties them together (KiCad sees one connected net). Real disconnection is
    # caught by the union-find OPEN NET GND test below -- that is the authority.
    if len(live_islands) > 1:
        print(f"note: GND pour spans {len(live_islands)} live islands "
              f"(electrically bridged; check OPEN NET GND below for real opens)")
    for net, group in sorted(by_net.items()):
        roots = {}
        for it in group:
            roots.setdefault(find(id(it)), []).append(it.label)
        if len(roots) > 1:
            parts = sorted(roots.values(), key=len, reverse=True)
            # the largest group is the main net; report what is stranded off it
            stranded = [",".join(sorted(p)) for p in parts[1:]]
            shown = " | ".join(stranded[:8])
            if len(stranded) > 8:
                shown += f" | (+{len(stranded) - 8} more)"
            errs.append(f"OPEN NET {net}: {len(roots)} islands; stranded "
                        f"from main: {shown}")
    return errs


def main():
    verbose = "-v" in sys.argv
    errs = check_courtyards()
    items = build_items()
    errs += check_keepout_copper(items)
    errs += check_edge_clearance(items)
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
