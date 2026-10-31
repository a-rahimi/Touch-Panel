"""Writes the files JLCPCB needs to make and assemble the board into pcb/fab/:

    touch_panel_gerbers.zip   copper, mask, paste, silkscreen, outline and drill files
    touch_panel_bom.csv       the BOM, in JLCPCB's columns, one row per LCSC part
    touch_panel_cpl.csv       where each part goes, in JLCPCB's columns

and the schematic as touch_panel_schematic.pdf. Everything comes from kicad-cli, run on
pcb/touch_panel.kicad_pcb and .kicad_sch; the pads, the shield tap and the mounting
holes are left out of the BOM and placement, because nothing is placed on them.
"""
import csv
import glob
import os
import shutil
import subprocess
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, ".."))
FAB = os.path.join(PCB, "fab")
CLI = os.path.expanduser("~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
BOARD = os.path.join(PCB, "touch_panel.kicad_pcb")
SCHEMATIC = os.path.join(PCB, "touch_panel.kicad_sch")
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"


def run(*args):
    r = subprocess.run([CLI, *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"kicad-cli {' '.join(args)} failed:\n{r.stdout}{r.stderr}")


def main():
    shutil.rmtree(FAB, ignore_errors=True)
    gerbers = os.path.join(FAB, "gerbers")
    os.makedirs(gerbers)

    run("pcb", "export", "gerbers", "--layers", LAYERS, "-o", gerbers + "/", BOARD)
    # plated and unplated holes in separate files, as fabs prefer
    run("pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm",
        "--excellon-separate-th", "-o", gerbers + "/", BOARD)
    with zipfile.ZipFile(os.path.join(FAB, "touch_panel_gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(glob.glob(os.path.join(gerbers, "*"))):
            z.write(f, os.path.basename(f))

    # BOM: KiCad's export grouped by value, footprint and LCSC number, then reshaped
    raw_bom = os.path.join(FAB, "kicad_bom.csv")
    run("sch", "export", "bom", "--fields", "Reference,Value,Footprint,LCSC,${QUANTITY}",
        "--group-by", "Value,Footprint,LCSC", "--ref-range-delimiter", "", "-o", raw_bom, SCHEMATIC)
    with open(raw_bom) as f, open(os.path.join(FAB, "touch_panel_bom.csv"), "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        rows = 0
        for r in csv.DictReader(f):
            if not r["LCSC"]:
                continue
            w.writerow([r["Value"], r["Reference"], r["Footprint"].split(":")[-1], r["LCSC"]])
            rows += 1
    os.remove(raw_bom)

    # Placement: KiCad's positions of the top-side parts, in JLCPCB's columns
    raw_pos = os.path.join(FAB, "kicad_pos.csv")
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front", "-o", raw_pos, BOARD)
    with open(raw_pos) as f, open(os.path.join(FAB, "touch_panel_cpl.csv"), "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        placed = 0
        for r in csv.DictReader(f):
            if r["Ref"][0] in "EH":
                continue
            w.writerow([r["Ref"], f'{float(r["PosX"]):.3f}mm', f'{float(r["PosY"]):.3f}mm',
                        "Top" if r["Side"] == "top" else "Bottom", f'{float(r["Rot"]):.0f}'])
            placed += 1
    os.remove(raw_pos)

    run("sch", "export", "pdf", "-o", os.path.join(FAB, "touch_panel_schematic.pdf"), SCHEMATIC)
    print(f"wrote {os.path.relpath(FAB)}: gerbers ({len(os.listdir(gerbers))} files), "
          f"BOM ({rows} lines), placement ({placed} parts), schematic PDF")


if __name__ == "__main__":
    main()
