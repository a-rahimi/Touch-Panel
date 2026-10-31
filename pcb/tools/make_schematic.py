"""Writes pcb/touch_panel.kicad_sch from design.py.

Parts are connected by net labels at their pin ends rather than by wires, which keeps
the generator simple and the drawing readable: two pins are connected exactly when
they carry labels with the same name. Unconnected pins get no-connect flags, and
PWR_FLAG symbols mark the nets that come from off the board (VBUS and GND), so the
electrical rules check passes. Run with KiCad's Python or any Python 3.
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design  # noqa: E402
from sexp import Q, dump, find, find_all, parse  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "touch_panel.kicad_sch")
SYMBOLS = os.path.expanduser("~/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols")
PROJECT = "touch_panel"

# A fixed namespace makes every uuid a function of its name, so regenerating the
# schematic leaves it unchanged unless the design changed, and the board can refer to
# the same symbol uuids (make_board.py links each footprint to its symbol this way).
NS = uuid.UUID("6f1d2a3c-5b4e-4c8f-9a7d-0e1f2a3b4c5d")


def uid(*name):
    return Q(str(uuid.uuid5(NS, "/".join(map(str, name)))))


ROOT = uid("root")

_libs = {}


def library_symbol(lib_id):
    """A library symbol, flattened if it extends another, named "Lib:Name"."""
    lib, name = lib_id.split(":")
    if lib not in _libs:
        _libs[lib] = parse(open(f"{SYMBOLS}/{lib}.kicad_sym").read())
    syms = {s[1]: s for s in find_all(_libs[lib], "symbol")}
    sym = syms[name]
    ext = find(sym, "extends")
    if ext:
        base = syms[ext[1]]
        props = find_all(sym, "property")
        body = [i for i in base[2:] if not (isinstance(i, list) and i[0] == "property")]
        # the base's unit sub-symbols are named after the base; rename them
        for i in body:
            if isinstance(i, list) and i[0] == "symbol":
                i[1] = Q(i[1].replace(ext[1], name, 1))
        sym = ["symbol", Q(name)] + props + body
    sym = [i for i in sym]
    sym[1] = Q(lib_id)
    return sym


def pins(sym):
    """(number, x, y, rotation, electrical type) of each pin, in library coordinates."""
    out = []
    for unit in find_all(sym, "symbol"):
        for p in find_all(unit, "pin"):
            at = find(p, "at")
            out.append((find(p, "number")[1], float(at[1]), float(at[2]), int(float(at[3])), p[1]))
    return out


def pin_names(lib_id):
    """Pin number to pin name, which KiCad uses to name an unconnected pin's net."""
    out = {}
    for unit in find_all(library_symbol(lib_id), "symbol"):
        for p in find_all(unit, "pin"):
            out[find(p, "number")[1]] = find(p, "name")[1]
    return out


def prop(name, value, x, y, hide=False):
    eff = ["effects", ["font", ["size", 1.27, 1.27]]]
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Q(name), Q(value or ""), ["at", x, y, 0], eff]


def instance(lib_id, ref, value, x, y, footprint="", extra=(), key=None):
    sym = library_symbol(lib_id)
    key = key or ref
    body = ["symbol", ["lib_id", Q(lib_id)], ["at", x, y, 0], ["unit", 1],
            ["exclude_from_sim", "no"], ["in_bom", "no" if ref.startswith(("#", "E", "H")) else "yes"],
            ["on_board", "no" if ref.startswith("#") else "yes"], ["dnp", "no"],
            ["uuid", uid("sym", key)],
            prop("Reference", ref, x, y - 2.54, hide=ref.startswith("#")),
            prop("Value", value, x, y + 2.54),
            prop("Footprint", footprint, x, y, hide=True),
            prop("Datasheet", "", x, y, hide=True)]
    for k, v in extra:
        body.append(prop(k, v, x, y, hide=True))
    for num, *_ in pins(sym):
        body.append(["pin", Q(num), ["uuid", uid("pin", key, num)]])
    body.append(["instances", ["project", Q(PROJECT), ["path", Q("/" + ROOT),
                                                        ["reference", Q(ref)], ["unit", 1]]]])
    return body


def label(net, x, y, angle):
    """A global label, so the net is named NET on the board, not /NET as a sheet-local
    label would make it."""
    just = {0: "left", 180: "right", 90: "left", 270: "right"}[angle]
    return ["global_label", Q(net), ["shape", "passive"], ["at", x, y, angle],
            ["fields_autoplaced", "yes"],
            ["effects", ["font", ["size", 1.27, 1.27]], ["justify", just]],
            ["uuid", uid("label", net, x, y)],
            ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", x, y, 0],
             ["effects", ["font", ["size", 1.27, 1.27]], ["justify", just], ["hide", "yes"]]]]


def pin_end(x, y, px, py):
    # library y points up and schematic y points down
    return round(x + px, 2), round(y - py, 2)


# Where each part goes on the sheet, in mm on the 1.27 mm grid.
def place():
    g = 1.27
    snap = lambda v: round(round(v / g) * g, 2)
    at = {"U1": (150, 120), "J1": (40, 60), "U3": (95, 50), "R15": (125, 40), "R16": (125, 60),
          "R13": (30, 115), "R14": (50, 115), "C1": (75, 115),
          "U2": (95, 150), "C2": (125, 150), "C3": (240, 150), "C4": (260, 150),
          "R17": (40, 160), "C5": (40, 185), "SW1": (60, 185),
          "R18": (40, 215), "SW2": (60, 225), "R19": (240, 215), "D1": (260, 215)}
    for i in range(12):
        at[f"R{i + 1}"] = (320 + i * 20, 70)
    for e in range(13):
        at[f"E{e + 1}"] = (320 + (e % 7) * 30, 130 + (e // 7) * 40)
    for i in range(6):
        at[f"H{i + 1}"] = (320 + i * 20, 230)
    return {k: (snap(x), snap(y)) for k, (x, y) in at.items()}


def main():
    at = place()
    lib_ids = sorted({p["symbol"] for p in design.PARTS} | {"power:PWR_FLAG"})
    items = []
    for p in design.PARTS:
        x, y = at[p["ref"]]
        extra = [("LCSC", p["lcsc"])] if p["lcsc"] else []
        items.append(instance(p["symbol"], p["ref"], p["value"], x, y, p["footprint"], extra))
        for num, px, py, rot, kind in pins(library_symbol(p["symbol"])):
            ex, ey = pin_end(x, y, px, py)
            net = p["pins"].get(num)
            if net:
                # the label points away from the body: a pin on the left side of a
                # symbol (rotation 0) gets a label reading leftwards, and so on
                items.append(label(net, ex, ey, {0: 180, 180: 0, 90: 270, 270: 90}[rot]))
            else:
                items.append(["no_connect", ["at", ex, ey], ["uuid", uid("nc", p["ref"], num)]])

    # VBUS and GND come from the USB connector, whose pins are passive, so each needs a
    # flag saying it is driven.
    for i, net in enumerate(["VBUS", "GND"]):
        x, y = 76.2 + 20.32 * i, 25.4
        items.append(instance("power:PWR_FLAG", f"#FLG0{i + 1}", "PWR_FLAG", x, y, key=f"flag{net}"))
        (num, px, py, rot, _), = pins(library_symbol("power:PWR_FLAG"))
        ex, ey = pin_end(x, y, px, py)
        items.append(label(net, ex, ey, 270))

    sch = ["kicad_sch", ["version", "20250114"], ["generator", Q("make_schematic.py")],
           ["generator_version", Q("10.0")], ["uuid", ROOT], ["paper", Q("A2")],
           ["title_block", ["title", Q("Touch panel")], ["rev", Q("1")],
            ["comment", 1, Q("Generated by pcb/tools/make_schematic.py from design.py")]],
           ["lib_symbols"] + [library_symbol(l) for l in lib_ids]]
    sch += items
    sch += [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
    with open(OUT, "w") as f:
        f.write(dump(sch) + "\n")
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
