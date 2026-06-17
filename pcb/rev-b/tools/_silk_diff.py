#!/usr/bin/env python3
"""Diff generated silk labels against the board's, matched by UUID.

generate_board emits each silk label with a deterministic uuid (uid("silk",
...)). KiCad preserves that uuid when a label is dragged, so any uuid whose
board position differs from the freshly-generated position is a label the user
moved. Prints those deltas as design-coordinate overrides (board - page_origin)
ready to paste into SILK_OVERRIDES.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import generate_board as G

PCB = os.path.join(os.path.dirname(__file__), "..", "sauna-rev-b.kicad_pcb")
OX, OY = G.BOARD.get("page_origin", (0, 0))


def blocks(t, tok):
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


# --- generated silk (in-memory, no file written) ---
b = G.Board.create_new()
G.silk_labels(b)
if OX or OY:
    G.translate_board(b, OX, OY)
gen = {}
for g in b.graphicItems:
    if g.__class__.__name__ == "GrText":
        gen[g.tstamp] = (g.text, round(g.position.X, 3), round(g.position.Y, 3),
                         round(g.position.angle or 0))

# --- board silk ---
t = open(PCB).read()
board = {}
for blk in blocks(t, "(gr_text "):
    mtxt = re.match(r'\(gr_text "([^"]*)"', blk)
    mat = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
    mlay = re.search(r'\(layer "([^"]+)"', blk)
    muid = re.search(r'\((?:uuid|tstamp)\s+"?([0-9a-fA-F-]{36})"?', blk)
    if mtxt and mat and mlay and muid and "SilkS" in mlay.group(1):
        board[muid.group(1)] = (mtxt.group(1), float(mat.group(1)),
                                float(mat.group(2)), round(float(mat.group(3)
                                or 0)))

print(f"generated silk labels: {len(gen)}   board silk labels: {len(board)}")
moved, missing = [], []
for u, (txt, gx, gy, ga) in gen.items():
    if u not in board:
        missing.append((txt, u))
        continue
    bt, bx, by, ba = board[u]
    if abs(bx - gx) > 0.05 or abs(by - gy) > 0.05 or ba != ga:
        moved.append((u, txt, (gx, gy, ga), (bx, by, ba)))

print(f"\n{len(moved)} label(s) moved by the user:")
for u, txt, gen_p, brd_p in sorted(moved, key=lambda m: m[1]):
    dx, dy = brd_p[0] - gen_p[0], brd_p[1] - gen_p[1]
    print(f"  {txt!r:>26}: gen {gen_p} -> board {brd_p}  "
          f"(Δ {dx:+.2f},{dy:+.2f})")
print("\n# paste-ready SILK_OVERRIDES entries (design coords = board-page_origin):")
for u, txt, gen_p, brd_p in sorted(moved, key=lambda m: m[1]):
    print(f'    "{u}": '
          f"({round(brd_p[0]-OX, 3)}, {round(brd_p[1]-OY, 3)}, "
          f"{brd_p[2]}),  # {txt}")
if missing:
    print(f"\n{len(missing)} generated label(s) with no uuid match on board:")
    for txt, u in missing:
        print(f"  {txt!r} ({u})")
extra = [u for u in board if u not in gen]
if extra:
    print(f"\n{len(extra)} board silk label(s) with no generated match "
          f"(added by hand?): {[board[u][0] for u in extra]}")
