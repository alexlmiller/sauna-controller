#!/usr/bin/env python3
"""Grid maze router for the Rev B board.

Routes every net in design.py on a 0.25 mm grid (F.Cu preferred, B.Cu as
crossing layer with cost penalty so the GND plane stays intact), then writes
the result to tools/routing.py for generate_board.py to consume.

GND is handled specially: every SMD GND pad gets a short stub + via to the
B.Cu plane; THT GND pads reach the plane directly.
"""
import heapq
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import design
from design import C, NETS, NET_CLASSES, BOARD
from footprints import FOOTPRINTS, MOUNTING_HOLE

PITCH = 0.5
W = int(round(BOARD["width"] / PITCH)) + 1
H = int(round(BOARD["height"] / PITCH)) + 1
MARGIN = 0.05          # extra safety on top of class clearance
VIA_R = 0.4
VIA_CLEAR = 0.5        # via block-map radius (> VIA_R for corner margin)
B_COST = 1.25          # multiplier for B.Cu steps (protect GND plane)
VIA_COST = 40          # in grid steps


def rot(px, py, angle):
    a = math.radians(angle)
    return (px * math.cos(a) + py * math.sin(a),
            -px * math.sin(a) + py * math.cos(a))


def clearance_of(net):
    if net is None:
        return 0.2
    return NET_CLASSES[NETS[net]]["clearance"]


def width_of(net):
    return NET_CLASSES[NETS[net]]["width"]


# --------------------------------------------------------------------------
# Obstacles: (layers, cx, cy, hx, hy, net)
# --------------------------------------------------------------------------
def build_obstacles():
    obs = []
    for ref in sorted(C):
        comp = C[ref]
        x, y, ang = comp["at"]
        for num, ptype, shape, (px, py), (sx, sy), drill in \
                FOOTPRINTS[comp["footprint"]]["pads"]:
            dx, dy = rot(px, py, ang)
            hx, hy = sx / 2, sy / 2
            if ang % 180 == 90:
                hx, hy = hy, hx
            layers = (True, False) if ptype == "smd" else (True, True)
            obs.append([layers, x + dx, y + dy, hx, hy,
                        comp["nets"].get(num), f"{ref}.{num}"])
    for i, (x, y) in enumerate(BOARD["mounting_holes"], start=1):
        r = MOUNTING_HOLE["pad"] / 2
        obs.append([(True, True), x, y, r, r, None, f"H{i}"])
    kx1, ky1, kx2, ky2 = BOARD["antenna_keepout"]
    obs.append([(True, True), (kx1 + kx2) / 2, (ky1 + ky2) / 2,
                (kx2 - kx1) / 2 + 0.2, (ky2 - ky1) / 2 + 0.2, "__KEEPOUT__",
                "keepout"])
    return obs


def block_map(obs, net, half):
    """cells where a trace centerline of given net may NOT be"""
    blocked = np.zeros((2, H, W), dtype=bool)
    # board edge
    e = int(math.ceil((half + 0.4) / PITCH))
    blocked[:, :e, :] = True
    blocked[:, -e:, :] = True
    blocked[:, :, :e] = True
    blocked[:, :, -e:] = True
    for layers, cx, cy, hx, hy, onet, _label in obs:
        if onet == net:
            continue
        oc = 0.3 if onet == "__KEEPOUT__" else clearance_of(onet)
        infl = half + max(clearance_of(net), oc) + MARGIN
        x1 = max(0, int((cx - hx - infl) / PITCH))
        x2 = min(W - 1, int(math.ceil((cx + hx + infl) / PITCH)))
        y1 = max(0, int((cy - hy - infl) / PITCH))
        y2 = min(H - 1, int(math.ceil((cy + hy + infl) / PITCH)))
        if x2 < x1 or y2 < y1:
            continue
        xs = np.arange(x1, x2 + 1) * PITCH
        ys = np.arange(y1, y2 + 1) * PITCH
        dx = np.maximum(np.abs(xs[None, :] - cx) - hx, 0)
        dy = np.maximum(np.abs(ys[:, None] - cy) - hy, 0)
        mask = (dx * dx + dy * dy) < infl * infl
        for li in (0, 1):
            if layers[li]:
                blocked[li, y1:y2 + 1, x1:x2 + 1] |= mask
    return blocked


def pad_cells(px, py, hx, hy):
    cells = []
    x1 = int(math.ceil((px - hx - 0.05) / PITCH))
    x2 = int((px + hx + 0.05) / PITCH)
    y1 = int(math.ceil((py - hy - 0.05) / PITCH))
    y2 = int((py + hy + 0.05) / PITCH)
    for cx in range(max(0, x1), min(W - 1, x2) + 1):
        for cy in range(max(0, y1), min(H - 1, y2) + 1):
            cells.append((cx, cy))
    if not cells:
        cells.append(cell_of(px, py))
    return cells


def cell_of(x, y):
    return (int(round(x / PITCH)), int(round(y / PITCH)))


def pos_of(cx, cy):
    return (round(cx * PITCH, 3), round(cy * PITCH, 3))


def dijkstra(blocked, via_ok, starts, targets, anchors=None,
             window_mm=25):
    """Weighted A*: starts/targets are sets of (layer, cx, cy)."""
    INF = 1e18
    txs = [t[1] for t in targets]
    tys = [t[2] for t in targets]
    sxs = [s[1] for s in starts] + txs
    sys_ = [s[2] for s in starts] + tys
    pad = int(window_mm / PITCH)
    wx1 = max(0, min(sxs) - pad)
    wx2 = min(W - 1, max(sxs) + pad)
    wy1 = max(0, min(sys_) - pad)
    wy2 = min(H - 1, max(sys_) + pad)
    if anchors is None:
        anchors = [(t[1], t[2]) for t in targets]
    if len(anchors) > 24:
        anchors = anchors[::max(1, len(anchors) // 24)]

    def h(cx, cy):
        return 1.6 * min(abs(cx - ax) + abs(cy - ay) for ax, ay in anchors)

    dist = {}
    prev = {}
    pq = []
    for s in starts:
        li, cx, cy = s
        if not blocked[li, cy, cx]:
            dist[s] = 0.0
            heapq.heappush(pq, (h(cx, cy), 0.0, s))
    end = None
    while pq:
        _f, d, node = heapq.heappop(pq)
        if d > dist.get(node, INF):
            continue
        if node in targets:
            end = node
            break
        li, cx, cy = node
        step = B_COST if li == 1 else 1.0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if wx1 <= nx <= wx2 and wy1 <= ny <= wy2 and \
                    not blocked[li, ny, nx]:
                nn = (li, nx, ny)
                nd = d + step
                if nd < dist.get(nn, INF):
                    dist[nn] = nd
                    prev[nn] = node
                    heapq.heappush(pq, (nd + h(nx, ny), nd, nn))
        oli = 1 - li
        if via_ok[cy, cx] and not blocked[oli, cy, cx]:
            nn = (oli, cx, cy)
            nd = d + VIA_COST
            if nd < dist.get(nn, INF):
                dist[nn] = nd
                prev[nn] = node
                heapq.heappush(pq, (nd + h(cx, cy), nd, nn))
    if end is None:
        return None
    path = [end]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    return path


def simplify(path):
    """collapse collinear runs; returns list of (layer, cx, cy) waypoints"""
    if len(path) <= 2:
        return path
    out = [path[0]]
    for i in range(1, len(path) - 1):
        a, b, c = out[-1], path[i], path[i + 1]
        if a[0] == b[0] == c[0]:
            d1 = (b[1] - a[1], b[2] - a[2])
            d2 = (c[1] - b[1], c[2] - b[2])
            n1 = (0 if d1[0] == 0 else d1[0] // abs(d1[0]),
                  0 if d1[1] == 0 else d1[1] // abs(d1[1]))
            if n1 == d2:
                continue
        out.append(b)
    out.append(path[-1])
    return out


def string_pull(way, blocked):
    """replace staircases between waypoints with L-shapes where possible"""
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(way) - 2:
            j = min(len(way) - 1, i + 12)
            while j > i + 1:
                a, b = way[i], way[j]
                if a[0] != b[0]:
                    j -= 1
                    continue
                li = a[0]
                ok_path = None
                for corner in ((a[1], b[2]), (b[1], a[2])):
                    cells = l_cells(a[1:], corner, b[1:])
                    if cells is not None and \
                            all(not blocked[li, cy, cx] for cx, cy in cells):
                        ok_path = [(li, corner[0], corner[1])]
                        break
                if ok_path is not None and way[i + 1:j] != ok_path:
                    way[i + 1:j] = ok_path
                    changed = True
                    break
                j -= 1
            i += 1
    return way


def l_cells(a, corner, b):
    cells = []
    for p, q in ((a, corner), (corner, b)):
        x1, y1 = p
        x2, y2 = q
        if x1 == x2:
            for y in range(min(y1, y2), max(y1, y2) + 1):
                cells.append((x1, y))
        elif y1 == y2:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                cells.append((x, y1))
        else:
            return None  # not an L
    return cells


def main():
    obs = build_obstacles()
    # collect pads per net
    net_pads = {}
    for ref in sorted(C):
        comp = C[ref]
        x, y, ang = comp["at"]
        for num, ptype, shape, (px, py), (sx, sy), drill in \
                FOOTPRINTS[comp["footprint"]]["pads"]:
            net = comp["nets"].get(num)
            if not net:
                continue
            dx, dy = rot(px, py, ang)
            tht = ptype != "smd"
            hx, hy = sx / 2, sy / 2
            if ang % 180 == 90:
                hx, hy = hy, hx
            net_pads.setdefault(net, []).append(
                (x + dx, y + dy, tht, f"{ref}.{num}", hx, hy))

    routes = []   # (net, layer, width, [pts])
    vias = []     # (net, (x, y))

    def add_obstacle_path(net, w, waypts):
        for k in range(len(waypts) - 1):
            (l1, x1, y1), (l2, x2, y2) = waypts[k], waypts[k + 1]
            if l1 != l2:
                vias.append((net, pos_of(x1, y1)))
                obs.append([(True, True), x1 * PITCH, y1 * PITCH,
                            VIA_R, VIA_R, net, "via"])
                continue
            ax, ay = x1 * PITCH, y1 * PITCH
            bx, by = x2 * PITCH, y2 * PITCH
            cx, cy = (ax + bx) / 2, (ay + by) / 2
            hx = abs(bx - ax) / 2 + w / 2
            hy = abs(by - ay) / 2 + w / 2
            obs.append([(l1 == 0, l1 == 1), cx, cy, hx, hy, net, "seg"])

    def emit_route(net, w, waypts, pad_a=None, pad_b=None):
        # split at layer changes into per-layer polylines
        runs = []
        cur = [waypts[0]]
        for p in waypts[1:]:
            if p[0] != cur[-1][0]:
                runs.append(cur)
                cur = [p]
            else:
                cur.append(p)
        runs.append(cur)
        for ri, run in enumerate(runs):
            pts = [pos_of(p[1], p[2]) for p in run]
            if ri == 0 and pad_a is not None:
                pts.insert(0, pad_a)
            if ri == len(runs) - 1 and pad_b is not None:
                pts.append(pad_b)
            pts = [p for i, p in enumerate(pts)
                   if i == 0 or p != pts[i - 1]]
            if len(pts) > 1:
                routes.append((net, "F.Cu" if run[0][0] == 0 else "B.Cu",
                               w, pts))

    # ---- 1. GND stubs + vias for SMD pads --------------------------------
    print("placing GND stubs...", flush=True)
    gnd_smd = [p for p in net_pads.get("GND", []) if not p[2]]
    gb = block_map(obs, "GND", 0.15)       # 0.3 wide stub
    vb = block_map(obs, "GND", VIA_CLEAR)
    for gx, gy, _tht, label, _hx, _hy in gnd_smd:
        placed = False
        cands = []
        for d in (0.0, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0):
            for ux, uy in ((0, 1), (0, -1), (1, 0), (-1, 0),
                           (0.707, 0.707), (-0.707, 0.707),
                           (0.707, -0.707), (-0.707, -0.707)):
                cands.append((gx + d * ux, gy + d * uy))
                if d == 0.0:
                    break
        for vx, vy in cands:
            cx, cy = cell_of(vx, vy)
            if not (0 <= cx < W and 0 <= cy < H):
                continue
            if vb[0, cy, cx] or vb[1, cy, cx]:
                continue
            # stub path along straight line must be clear on F.Cu
            steps = max(1, int(math.hypot(vx - gx, vy - gy) / PITCH))
            ok = True
            for t in range(steps + 1):
                sx = gx + (vx - gx) * t / steps
                sy = gy + (vy - gy) * t / steps
                scx, scy = cell_of(sx, sy)
                if gb[0, scy, scx]:
                    ok = False
                    break
            if not ok:
                continue
            vpos = pos_of(cx, cy)
            if (vpos[0] - gx) ** 2 + (vpos[1] - gy) ** 2 > 0.01:
                routes.append(("GND", "F.Cu", 0.3, [(gx, gy), vpos]))
                ax, ay = (gx + vpos[0]) / 2, (gy + vpos[1]) / 2
                obs.append([(True, False), ax, ay,
                            abs(vpos[0] - gx) / 2 + 0.15,
                            abs(vpos[1] - gy) / 2 + 0.15, "GND", "gstub"])
            vias.append(("GND", vpos))
            obs.append([(True, True), vpos[0], vpos[1], VIA_R, VIA_R,
                        "GND", "gvia"])
            placed = True
            break
        if not placed:
            print(f"  !! no via spot for GND pad {label} at {gx},{gy}")

    # ---- 2. signal/power nets ---------------------------------------------
    order = ["+24V", "+24V_LED", "LED_R-", "LED_G-", "LED_B-", "LED_W-",
             "COIL-", "SRL250_RTN", "+24V_SAFE", "+24V_LOGIC", "+5V",
             "+5V_PANEL", "+3V3",
             "GPIO19", "GPIO18", "GPIO17", "GPIO16", "GPIO13",
             "G_R", "G_G", "G_B", "G_W", "G_COIL",
             "DOOR_IN", "BENCH_DATA", "CEIL_DATA",
             "GPIO32", "GPIO33", "GPIO25", "GPIO22", "GPIO23",
             "GPIO26", "GPIO27", "GPIO14", "GPIO4",
             "AUX_IN", "AUX_LED", "HL_LED", "SPARE_IN", "SPARE_LED",
             "PANEL_TX", "PANEL_RX",
             "FAULT_A", "LED24_A", "LED5_A"]
    order.remove("+24V_SAFE")
    order.append("+24V_SAFE")
    missing = set(NETS) - set(order) - {"GND"}
    assert not missing, missing

    failures = []
    t0 = time.time()
    for net in order:
        pads = net_pads.get(net, [])
        if len(pads) < 2:
            continue
        w = width_of(net)
        half = w / 2
        # connect greedily: nearest unconnected pad to connected set
        connected = [pads[0]]
        remaining = pads[1:]
        net_cells = set()
        net_pts = {}
        for cx, cy in pad_cells(pads[0][0], pads[0][1],
                                pads[0][4], pads[0][5]):
            for li in ((0, 1) if pads[0][2] else (0,)):
                net_cells.add((li, cx, cy))
                net_pts[(li, cx, cy)] = (pads[0][0], pads[0][1])
        blocked = block_map(obs, net, half)
        vb = block_map(obs, net, VIA_CLEAR)
        via_ok = ~(vb[0] | vb[1])
        while remaining:
            remaining.sort(key=lambda p: min(
                (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 for q in connected))
            pad = remaining.pop(0)
            pc = cell_of(pad[0], pad[1])
            starts = set()
            for cx, cy in pad_cells(pad[0], pad[1], pad[4], pad[5]):
                for li in ((0, 1) if pad[2] else (0,)):
                    if not blocked[li, cy, cx]:
                        starts.add((li, cx, cy))
            if not starts:
                starts = {(0, pc[0], pc[1])}
            anchors = [cell_of(q[0], q[1]) for q in connected]
            path = dijkstra(blocked, via_ok, starts, net_cells,
                            anchors=anchors)
            if path is None:
                path = dijkstra(blocked, via_ok, starts, net_cells,
                                anchors=anchors, window_mm=200)
            if path is None:
                failures.append((net, pad[3]))
                print(f"  !! FAILED {net}: {pad[3]}", flush=True)
                connected.append(pad)
                continue
            path = simplify(path)
            way = string_pull(path, blocked)
            way = simplify(way)
            end_pt = net_pts.get(way[-1])
            emit_route(net, w, way, pad_a=(pad[0], pad[1]), pad_b=end_pt)
            add_obstacle_path(net, w, way)
            # grow target set with every cell of the path (re-trace cells)
            full = []
            for k in range(len(way) - 1):
                (l1, x1, y1), (l2, x2, y2) = way[k], way[k + 1]
                if l1 != l2:
                    full.append(way[k + 1])
                    continue
                steps = max(abs(x2 - x1), abs(y2 - y1))
                for t in range(steps + 1):
                    full.append((l1, x1 + (x2 - x1) * t // max(steps, 1),
                                 y1 + (y2 - y1) * t // max(steps, 1)))
            for c in full:
                net_cells.add(c)
            for cx, cy in pad_cells(pad[0], pad[1], pad[4], pad[5]):
                for li in ((0, 1) if pad[2] else (0,)):
                    net_cells.add((li, cx, cy))
                    net_pts.setdefault((li, cx, cy), (pad[0], pad[1]))
            connected.append(pad)
        print(f"routed {net}: {len(pads)} pads "
              f"({time.time() - t0:.1f}s)", flush=True)

    # ---- write routing.py --------------------------------------------------
    out = os.path.join(os.path.dirname(__file__), "routing.py")
    with open(out, "w") as f:
        f.write('"""AUTO-GENERATED by autoroute.py - do not edit by hand.\n'
                'ROUTES: (net, layer, width, [(x,y), ...]); VIAS: (net,(x,y))\n'
                '"""\n')
        f.write("ROUTES = [\n")
        for r in routes:
            f.write(f"    {r!r},\n")
        f.write("]\n\nVIAS = [\n")
        for v in vias:
            f.write(f"    {v!r},\n")
        f.write("]\n")
    print(f"\nwrote {out}: {len(routes)} routes, {len(vias)} vias, "
          f"{len(failures)} failures")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
