"""Writes the project's footprints into pcb/touch_panel.pretty.

Electrode is one pad of the panel, copper on the top layer with solder mask over it, so
a hand never touches bare copper. ShieldTap is a small bottom-layer pad that the shield
zone connects to, standing in for the shield in the schematic. Both are left out of the
BOM and the placement file, because nothing is placed on them.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402
from sexp import Q, dump  # noqa: E402

OUT = os.path.join(HERE, "..", "touch_panel.pretty")


def footprint(name, descr, layer, pad_size, pad_layers, fab):
    w, h = pad_size
    return ["footprint", Q(name), ["version", "20241229"], ["generator", Q("make_footprints.py")],
            ["layer", Q(layer)], ["descr", Q(descr)],
            ["property", Q("Reference"), Q("REF**"), ["at", 0, -h / 2 - 1.5, 0], ["layer", Q(fab)],
             ["effects", ["font", ["size", 1, 1], ["thickness", 0.15]]]],
            ["property", Q("Value"), Q(name), ["at", 0, h / 2 + 1.5, 0], ["layer", Q(fab)],
             ["effects", ["font", ["size", 1, 1], ["thickness", 0.15]]]],
            ["attr", "exclude_from_pos_files", "exclude_from_bom"],
            ["fp_rect", ["start", -w / 2, -h / 2], ["end", w / 2, h / 2],
             ["stroke", ["width", 0.1], ["type", "default"]], ["fill", "no"], ["layer", Q(fab)]],
            ["pad", Q("1"), "smd", "rect", ["at", 0, 0], ["size", w, h],
             ["layers"] + [Q(l) for l in pad_layers]]]


os.makedirs(OUT, exist_ok=True)
pad = (round(design.CELL_W - design.GAP, 3), round(design.CELL_H - design.GAP, 3))
for name, fp in [
    ("Electrode", footprint("Electrode",
                            f"Touch pad {pad[0]} x {pad[1]} mm, top copper under solder mask",
                            "F.Cu", pad, ["F.Cu"], "F.Fab")),
    # drawn on the top like any footprint; make_board.py flips it to the bottom
    ("ShieldTap", footprint("ShieldTap", "Tap for the shield zone, placed on the bottom layer",
                            "F.Cu", (1.5, 1.5), ["F.Cu"], "F.Fab")),
]:
    with open(os.path.join(OUT, name + ".kicad_mod"), "w") as f:
        f.write(dump(fp) + "\n")
print("wrote", ", ".join(os.listdir(OUT)), "in", os.path.normpath(OUT))
