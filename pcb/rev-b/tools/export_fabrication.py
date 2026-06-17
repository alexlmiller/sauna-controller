#!/usr/bin/env python3
"""Regenerate Rev B fabrication outputs from the current KiCad PCB.

Outputs:
  fabrication/sauna-rev-b-bom.csv
  fabrication/sauna-rev-b-cpl.csv
  fabrication/gerbers/*
  fabrication/sauna-rev-b-gerbers.zip
"""
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "sauna-rev-b.kicad_pcb"
FAB = ROOT / "fabrication"
GERBERS = FAB / "gerbers"
BOM = FAB / "sauna-rev-b-bom.csv"
CPL = FAB / "sauna-rev-b-cpl.csv"
ZIP = FAB / "sauna-rev-b-gerbers.zip"
LAYERS = ",".join([
    "F.Cu", "B.Cu",
    "F.Paste", "B.Paste",
    "F.Silkscreen", "B.Silkscreen",
    "F.Mask", "B.Mask",
    "Edge.Cuts",
])


def run(*args):
    print("+", " ".join(str(a) for a in args))
    subprocess.run(args, cwd=ROOT, check=True)


def kicad_cli():
    path = shutil.which("kicad-cli")
    if not path:
        raise SystemExit("kicad-cli not found on PATH")
    return path


def format_rotation(value):
    rot = float(value)
    if rot == int(rot):
        return str(int(rot))
    return f"{rot:.4f}".rstrip("0").rstrip(".")


def export_cpl(cli):
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "positions.csv"
        run(cli, "pcb", "export", "pos",
            "--format", "csv",
            "--units", "mm",
            "--side", "front",
            "--exclude-dnp",
            "--output", raw,
            PCB)
        with raw.open(newline="") as f:
            rows = list(csv.DictReader(f))

    with CPL.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in rows:
            writer.writerow([
                row["Ref"],
                f"{float(row['PosX']):.4f}",
                f"{float(row['PosY']):.4f}",
                "Top" if row["Side"].lower() == "top" else "Bottom",
                format_rotation(row["Rot"]),
            ])
    print(f"wrote {CPL} ({len(rows)} placements)")


def export_gerbers(cli):
    if GERBERS.exists():
        shutil.rmtree(GERBERS)
    GERBERS.mkdir(parents=True)

    run(cli, "pcb", "export", "gerbers",
        "--output", GERBERS,
        "--layers", LAYERS,
        "--subtract-soldermask",
        "--no-protel-ext",
        PCB)
    run(cli, "pcb", "export", "drill",
        "--output", GERBERS,
        "--excellon-units", "mm",
        "--excellon-separate-th",
        PCB)

    files = sorted(p for p in GERBERS.iterdir() if p.is_file())
    if len(files) != 12:
        names = "\n".join(f"  {p.name}" for p in files)
        raise SystemExit(f"expected 12 gerber/drill/job files, got {len(files)}:\n{names}")

    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.name)
    print(f"wrote {ZIP} ({len(files)} files)")


def main():
    cli = kicad_cli()
    run(sys.executable, ROOT / "tools" / "generate_bom.py")
    if not BOM.exists():
        raise SystemExit(f"BOM was not generated: {BOM}")
    export_cpl(cli)
    export_gerbers(cli)


if __name__ == "__main__":
    main()
