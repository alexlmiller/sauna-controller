#!/usr/bin/env python3
"""Verify generate_board.py reproduces the actual board -- by VALUE, not uuid.

`_silk_diff.py` matches silk by uuid and only flags position/rotation deltas, so
a pure text edit (e.g. renaming a connector header in KiCad, which keeps the
uuid) is invisible to it. This tool regenerates the board in memory from the
current source (design.py + routing.py + generate_board.py) and diffs it against
sauna-rev-b.kicad_pcb three ways:

  * footprints -- by reference, position + rotation
  * silk text  -- by TEXT + position (catches renames, additions, deletions)
  * silk lines -- top-level F.SilkS line geometry
  * traces     -- segment geometry as a multiset

Run it after editing the board in KiCad (alongside _design_diff / import_routing)
to confirm every hand change is captured in the source before regenerating --
i.e. that a regenerate won't revert anything. Exit code 0 = faithful repro.

  tools/_repro_check.py            # checks ../sauna-rev-b.kicad_pcb
"""
import os
import re
import sys
import collections

sys.path.insert(0, os.path.dirname(__file__))
import importlib
import design
import routing
import footprints
import generate_board as G
for _m in (design, routing, footprints, G):
    importlib.reload(_m)

PCB = os.path.join(os.path.dirname(__file__), "..", "sauna-rev-b.kicad_pcb")
FP_TOL = 0.02      # mm: footprint placement tolerance
SILK_TOL = 0.10    # mm: silk position tolerance (text must match exactly)


def build_generated():
    """Mirror generate_board.main() without writing a file."""
    b = G.Board.create_new()
    G.board_outline(b)
    for ref in sorted(G.C):
        b.footprints.append(G.build_footprint(ref, G.C[ref]))
    for i, (x, y) in enumerate(G.BOARD["mounting_holes"], start=1):
        b.footprints.append(G.mounting_hole(i, x, y))
    G.silk_labels(b)
    G.zones(b)
    G.traces(b)
    ox, oy = G.BOARD.get("page_origin", (0, 0))
    if ox or oy:
        G.translate_board(b, ox, oy)
    return b


def gen_views(b):
    fps = {}
    for fp in b.footprints:
        ref = next((gi.text for gi in fp.graphicItems
                    if getattr(gi, "type", None) == "reference"), None)
        if ref:
            fps[ref] = (round(fp.position.X, 3), round(fp.position.Y, 3),
                        round((fp.position.angle or 0) % 360))
    silk = [(g.text, round(g.position.X, 2), round(g.position.Y, 2),
             round(g.position.angle or 0)) for g in b.graphicItems
            if g.__class__.__name__ == "GrText"]
    silk_lines, seg, via = [], [], []
    for g in b.graphicItems:
        if g.__class__.__name__ == "GrLine" and g.layer == "F.SilkS":
            silk_lines.append((round(g.start.X, 2), round(g.start.Y, 2),
                               round(g.end.X, 2), round(g.end.Y, 2),
                               round(getattr(g, "width", 0.15) or 0.15, 3)))
    for tr in b.traceItems:
        if tr.__class__.__name__ == "Segment":
            seg.append((round(tr.start.X, 2), round(tr.start.Y, 2),
                        round(tr.end.X, 2), round(tr.end.Y, 2),
                        round(tr.width, 3), tr.layer))
        elif tr.__class__.__name__ == "Via":
            via.append((round(tr.position.X, 2), round(tr.position.Y, 2)))
    return fps, silk, silk_lines, seg, via


def _blocks(t, tok):
    out, i = [], 0
    while True:
        i = t.find(tok, i)
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


def board_views(t):
    fps = {}
    for blk in _blocks(t, "(footprint "):
        mref = re.search(r'\(property "Reference" "([^"]+)"', blk) or \
            re.search(r'\(fp_text\s+reference "([^"]+)"', blk)
        mat = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
        if mref and mat:
            fps[mref.group(1)] = (round(float(mat.group(1)), 3),
                                  round(float(mat.group(2)), 3),
                                  round((float(mat.group(3) or 0)) % 360))
    silk = []
    for blk in _blocks(t, "(gr_text "):
        mt = re.match(r'\(gr_text "([^"]*)"', blk)
        mat = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
        mlay = re.search(r'\(layer "([^"]+)"', blk)
        if mt and mat and mlay and "SilkS" in mlay.group(1):
            silk.append((mt.group(1), round(float(mat.group(1)), 2),
                         round(float(mat.group(2)), 2),
                         round(float(mat.group(3) or 0))))
    silk_lines = []
    for blk in _blocks(t, "(gr_line"):
        start = re.search(r'\(start ([-\d.]+) ([-\d.]+)\)', blk)
        end = re.search(r'\(end ([-\d.]+) ([-\d.]+)\)', blk)
        mlay = re.search(r'\(layer "([^"]+)"', blk)
        width = re.search(r'\(stroke\s+\(width ([-\d.]+)\)', blk) or \
            re.search(r'\(width ([-\d.]+)\)', blk)
        if start and end and mlay and mlay.group(1) == "F.SilkS":
            silk_lines.append((round(float(start.group(1)), 2),
                               round(float(start.group(2)), 2),
                               round(float(end.group(1)), 2),
                               round(float(end.group(2)), 2),
                               round(float(width.group(1)) if width else 0.15, 3)))
    seg = []
    for m in re.finditer(
            r'\(segment\s+\(start ([-\d.]+) ([-\d.]+)\)\s+\(end ([-\d.]+) '
            r'([-\d.]+)\)\s+\(width ([-\d.]+)\)\s+\(layer "([^"]+)"\)', t):
        x1, y1, x2, y2, w, lay = m.groups()
        seg.append((round(float(x1), 2), round(float(y1), 2),
                    round(float(x2), 2), round(float(y2), 2),
                    round(float(w), 3), lay))
    via = []
    for m in re.finditer(r'\(via\b(.*?)\(net ', t, re.S):
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)\)', m.group(1))
        if at and "(via" not in m.group(1):
            via.append((round(float(at.group(1)), 2), round(float(at.group(2)), 2)))
    return fps, silk, silk_lines, seg, via


def main():
    gfp, gsilk, gsilk_lines, gseg, gvia = gen_views(build_generated())
    bfp, bsilk, bsilk_lines, bseg, bvia = board_views(open(PCB).read())
    bad = 0

    # --- footprints ---
    print("=== FOOTPRINTS ===")
    fpbad = 0
    for ref in sorted(set(gfp) | set(bfp)):
        g, b = gfp.get(ref), bfp.get(ref)
        if g is None:
            print(f"  only on BOARD: {ref} {b}")
            fpbad += 1
        elif b is None:
            print(f"  only in GEN:   {ref} {g}")
            fpbad += 1
        elif abs(g[0] - b[0]) > FP_TOL or abs(g[1] - b[1]) > FP_TOL \
                or g[2] != b[2]:
            print(f"  MISMATCH {ref}: gen {g} board {b}")
            fpbad += 1
    print(f"  gen {len(gfp)}, board {len(bfp)}, mismatches {fpbad}")
    bad += fpbad

    # --- silk by text + position ---
    print("\n=== SILK (text + position) ===")
    bs = list(bsilk)
    moved, unmatched_gen = [], []
    for g in gsilk:
        same = [(i, b) for i, b in enumerate(bs) if b[0] == g[0]]
        hit = next((i for i, b in same
                    if abs(b[1] - g[1]) <= SILK_TOL and abs(b[2] - g[2]) <= SILK_TOL
                    and b[3] == g[3]), None)
        if hit is not None:
            bs.pop(hit)
        elif same:                       # same text exists but moved/rotated
            i, b = same[0]
            moved.append((g, b))
            bs.pop(i)
        else:
            unmatched_gen.append(g)
    print(f"  gen {len(gsilk)}, board {len(bsilk)}")
    if moved:
        print(f"  MOVED ({len(moved)}):")
        for g, b in sorted(moved):
            print(f"    {g[0]!r}: gen ({g[1]},{g[2]},{g[3]}) -> "
                  f"board ({b[1]},{b[2]},{b[3]})")
    if unmatched_gen:
        print(f"  in GEN, not on board ({len(unmatched_gen)}) "
              f"[deleted or text-changed on board]:")
        for g in sorted(unmatched_gen):
            print(f"    {g[0]!r} @ ({g[1]},{g[2]},{g[3]})")
    if bs:
        print(f"  on BOARD, not in gen ({len(bs)}) "
              f"[added or text-changed in KiCad]:")
        for b in sorted(bs):
            print(f"    {b[0]!r} @ ({b[1]},{b[2]},{b[3]})")
    bad += len(moved) + len(unmatched_gen) + len(bs)

    # --- silk lines (multiset, direction-insensitive) ---
    print("\n=== SILK LINES ===")

    def canon_line(s):
        a, b2 = sorted([(s[0], s[1]), (s[2], s[3])])
        return (a[0], a[1], b2[0], b2[1], s[4])
    gl = collections.Counter(canon_line(s) for s in gsilk_lines)
    bl = collections.Counter(canon_line(s) for s in bsilk_lines)
    ogl, obl = gl - bl, bl - gl
    print(f"  gen {len(gsilk_lines)}, board {len(bsilk_lines)}; "
          f"only-gen {sum(ogl.values())}, only-board {sum(obl.values())}")
    for s, c in list(ogl.items())[:6]:
        print(f"    GEN  x{c}: {s}")
    for s, c in list(obl.items())[:6]:
        print(f"    BRD  x{c}: {s}")
    bad += sum(ogl.values()) + sum(obl.values())

    # --- traces (multiset, direction-insensitive) ---
    print("\n=== TRACES ===")

    def canon(s):
        a, b2 = sorted([(s[0], s[1]), (s[2], s[3])])
        return (a[0], a[1], b2[0], b2[1], s[4], s[5])
    gc = collections.Counter(canon(s) for s in gseg)
    bc = collections.Counter(canon(s) for s in bseg)
    og, ob = gc - bc, bc - gc
    print(f"  gen {len(gseg)}, board {len(bseg)}; "
          f"only-gen {sum(og.values())}, only-board {sum(ob.values())}")
    for s, c in list(og.items())[:6]:
        print(f"    GEN  x{c}: {s}")
    for s, c in list(ob.items())[:6]:
        print(f"    BRD  x{c}: {s}")
    bad += sum(og.values()) + sum(ob.values())

    # --- vias (multiset) ---
    gv, bv = collections.Counter(gvia), collections.Counter(bvia)
    ogv, obv = gv - bv, bv - gv
    print(f"\n=== VIAS ===\n  gen {len(gvia)}, board {len(bvia)}; "
          f"only-gen {sum(ogv.values())}, only-board {sum(obv.values())}")
    for v, c in list(ogv.items())[:6]:
        print(f"    GEN x{c}: {v}")
    for v, c in list(obv.items())[:6]:
        print(f"    BRD x{c}: {v}")
    bad += sum(ogv.values()) + sum(obv.values())

    print(f"\n{'OK -- faithful reproduction' if bad == 0 else f'{bad} difference(s)'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
