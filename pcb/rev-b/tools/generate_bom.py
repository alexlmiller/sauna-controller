#!/usr/bin/env python3
"""Generate the JLCPCB assembly BOM CSV from design.py.

Goal: every part JLC-assemblable (SMD or JLC through-hole), no hand soldering.
LCSC numbers are validated from the Rev A match-review, confident picks, or
researched from LCSC -- every assembled part now carries a JLCPCB part number
(still verify in-stock + footprint/pitch in the JLC UI before ordering). Test
points are DNP (bare copper pads).

Outputs ../fabrication/sauna-rev-b-bom.csv  (Comment, Designator, Footprint,
JLCPCB Part #). Export the CPL (placement) + Gerbers from KiCad on the board.
"""
import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from design import C

# (footprint, value) -> LCSC.  "" = specify for JLC auto-match (verify in UI).
# value None in key = match any value for that footprint.
LCSC = {
    # --- validated in pcb/rev-a fabrication match-review ---
    ("R_0805", "100R"): "C17408", ("R_0805", "10K"): "C17414",
    ("R_0805", "1K"): "C17513", ("R_0805", "4K7"): "C17673",
    ("TO252", "AOD4184A"): "C99124", ("D_SMA", "SS54"): "C22452",
    ("D_SMB", "SMBJ30CA"): "C5331115",
    ("LED_0805", "GREEN 24V"): "C2297", ("LED_0805", "GREEN 5V"): "C2297",
    ("LED_0805", "RED FAULT"): "C2295", ("LED_0805", "RED ACT"): "C2295",
    ("SOCKET_1x19", None): "C319202",
    # Terminal blocks: Kangnex WJ2EDGV vertical-entry, plain/no flange.
    ("MKDS_2", None): "C8461",
    ("MKDS_3", None): "C8438",
    ("MKDS_4", None): "C8429",
    ("MKDS_5", None): "C8433",
    # --- confident picks (common JLC Basic parts) ---
    ("C_0805", "100nF"): "C49678",
    ("D_SOD323", "1N4148WS"): "C2128",   # 1N4148WS SOD-323, JLC Basic. (C8550 was
                                         # a 1SS181 in SOT-23 -- JLC flagged the
                                         # footprint mismatch; C2128 is the real part.)
    ("SOT23_6", "USBLC6-2SC6"): "C7519",
    # --- resolved this round (verify in-stock variant / pitch in JLC UI) ---
    ("SIP3_REG", None): "C18212380",     # K7805-2000R3 (YLPTEC) 5V/2A 8-36V SIP-3.
    # Drop-in for the SIP-3 footprint; ~1.1k JLC assembly stock. (C970791 was the
    # same part with more listed stock but turned out unavailable; DEXU C2931187
    # had 0.) ~$2.6-3 ea -- in-stock premium vs the $1.28 DEXU, no rework needed.
    # --- matched 2026-06 from LCSC (researched; verify stock in the JLC UI) ---
    ("R_1206", "3K3"): "C104771",        # RALEC RTT06332JTP 3.3k 5% 1206 250mW
    # (~4.6k JLC stock). Replaces C26032 (UNI-ROYAL 1%) which had only ~3 in JLC
    # pre-stock. Alt: C26041 (UNI-ROYAL 1206W4J0332T5E, 3.3k 5%, ~1k stock). 5%
    # is fine -- R1/R2 are opto LED current-limits (~7mA @ 24V), not precision.
    ("C_1210", "10uF 50V"): "C138687",   # Samsung CL32B106KBJNNNE X7R 1210
    ("C_1210", "22uF 25V"): "C52306",    # Samsung CL32A226KAJNNNE X5R 1210
    ("D_SMB", "SMBJ33A"): "C78419",      # Brightking SMBJ33A 600W unidir TVS (SMB)
    ("D_SOD923", "ESD9B5.0"): "C111566",  # onsemi ESD9B5.0ST5G SOD-923
    ("R_1812", "750mA PTC"): "C208467",  # Bourns MF-MSMF075/24-2 (24V, 1812)
    ("PTC_1812", "750mA PTC (COIL)"): "C208467",
    ("PTC_1812", "750mA PTC (LOGIC)"): "C208467",
    # Larger 2920 PTCs must be matched in the JLC upload UI. Keep these blank
    # until stock/current/voltage are confirmed against an actual JLC part.
    ("PTC_2920", "3A PTC (LED)"): "C719172",
    ("PTC_2920", "2A PTC (AUX)"): "C139284",
    ("SOP4_OPTO", "LTV-817S"): "C109227",  # Lite-On LTV-817S-TA1-C SOP-4
    ("CP_D8_P3.5", "220uF 50V"): "C106658",  # 220uF 50V radial D8xL16mm, 3.5mm pitch
}

# short footprint -> descriptive name for the BOM / JLC auto-match hint
FP = {
    "R_0805": "R0805", "C_0805": "C0805", "R_1206": "R1206", "C_1210": "C1210",
    "R_1812": "R1812", "PTC_1812": "PTC1812", "PTC_2920": "PTC2920",
    "D_SMA": "SMA,DO-214AC", "D_SMB": "SMB,DO-214AA",
    "D_SOD323": "SOD-323", "D_SOD923": "SOD-923", "TO252": "TO-252-2,DPAK",
    "SOT23_6": "SOT-23-6", "SOP4_OPTO": "SOP-4", "LED_0805": "LED0805",
    "SIP3_REG": "SIP-3,2.54mm", "MKDS_2": "Terminal 5.08mm 2P",
    "MKDS_3": "Terminal 5.08mm 3P", "MKDS_4": "Terminal 5.08mm 4P",
    "MKDS_5": "Terminal 5.08mm 5P", "SOCKET_1x19": "1x19 2.54mm female header",
    "CP_D8_P3.5": "Radial D8.0mm P3.50mm", "TESTPOINT": "TestPoint",
}

DNP_FP = {"TESTPOINT"}     # bare copper test pads -- not assembled


def lcsc_for(footprint, value):
    """LCSC part # for a (footprint, value); '' if unmatched / not assembled.
    Imported by generate_schematic.py to stamp the symbol LCSC field, so the
    schematic and this BOM can't disagree about part numbers."""
    if footprint in DNP_FP:
        return ""
    return LCSC.get((footprint, value), LCSC.get((footprint, None), ""))


def main():
    groups = defaultdict(list)
    for ref, c in C.items():
        groups[(c["footprint"], c["value"])].append(ref)

    out = os.path.join(os.path.dirname(__file__), "..", "fabrication",
                       "sauna-rev-b-bom.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    rows, dnp, blanks = [], [], []
    for (fp, val), refs in sorted(groups.items()):
        if fp in DNP_FP:
            dnp += refs
            continue
        lcsc = lcsc_for(fp, val)
        desig = ",".join(sorted(refs, key=lambda r: (r[0], int(
            "".join(ch for ch in r if ch.isdigit()) or 0))))
        rows.append((val, desig, FP.get(fp, fp), lcsc))
        if not lcsc:
            blanks.append(f"{val} [{fp}] x{len(refs)}")

    rows.sort(key=lambda r: (r[3] == "", r[2]))
    with open(out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Comment", "Designator", "Footprint", "JLCPCB Part #"])
        w.writerows(rows)

    total = sum(len(v) for v in groups.values())
    assembled = sum(len(r[1].split(",")) for r in rows)
    with_lcsc = sum(len(r[1].split(",")) for r in rows if r[3])
    print(f"wrote {out}")
    print(f"  {len(rows)} assembly lines, {assembled} parts "
          f"({with_lcsc} with LCSC, {assembled - with_lcsc} for JLC auto-match)")
    print(f"  DNP (not assembled): {len(dnp)} test points {sorted(dnp)}")
    print(f"  total board parts: {total}")
    print("\n  needs LCSC verification / auto-match:")
    for b in blanks:
        print(f"    - {b}")


if __name__ == "__main__":
    main()
