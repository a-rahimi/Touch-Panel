"""Writes pcb/sym-lib-table and pcb/fp-lib-table, the project's library tables.

They name every KiCad library design.py uses, through KiCad's own path variables, so
the project opens wherever KiCad 10 is installed, even one that was never configured
with global library tables. The project's own footprints are in touch_panel.pretty.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402

PCB = os.path.join(HERE, "..")


def row(name, uri, descr=""):
    return f'\t(lib (name "{name}") (type "KiCad") (uri "{uri}") (options "") (descr "{descr}"))\n'


symbols = sorted({p["symbol"].split(":")[0] for p in design.PARTS} | {"power"})
footprints = sorted({p["footprint"].split(":")[0] for p in design.PARTS} - {"touch_panel"})

with open(os.path.join(PCB, "sym-lib-table"), "w") as f:
    f.write("(sym_lib_table\n\t(version 7)\n")
    for lib in symbols:
        f.write(row(lib, f"${{KICAD10_SYMBOL_DIR}}/{lib}.kicad_sym"))
    f.write(")\n")

with open(os.path.join(PCB, "fp-lib-table"), "w") as f:
    f.write("(fp_lib_table\n\t(version 7)\n")
    for lib in footprints:
        f.write(row(lib, f"${{KICAD10_FOOTPRINT_DIR}}/{lib}.pretty"))
    f.write(row("touch_panel", "${KIPRJMOD}/touch_panel.pretty", "The pads and the shield tap"))
    f.write(")\n")

print("symbol libraries:", ", ".join(symbols))
print("footprint libraries:", ", ".join(footprints + ["touch_panel"]))
