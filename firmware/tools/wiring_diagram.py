"""Draws docs/wiring.svg, the touch panel's wiring diagram.

The panel is drawn from the back, where the wiring is done, at 40 px per inch, so the
electrode columns are mirrored relative to the front. Run: python3 firmware/tools/wiring_diagram.py
"""
import os

W, H = 1340, 840
C = dict(gnd="#222222", v33="#8e44ad", sda="#1f6fb4", scl="#e67e00", irq="#2a9d3a",
         lead="#b5651d", pad="#f3d9b1", padedge="#c8955a", box="#f4f6f8", edge="#55606b",
         text="#1d2329", muted="#6b7680", nc="#b0b7be", wood="#faf6ef")
out = []
def add(s): out.append(s)
def text(x, y, s, size=13, anchor="start", weight="normal", fill=C["text"], italic=False):
    st = ' font-style="italic"' if italic else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}"{st}>{s}</text>')
def board(x, y, w, h, title, sub=""):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{C["box"]}" stroke="{C["edge"]}" stroke-width="1.6"/>')
    text(x + w/2, y + 22, title, 15, "middle", "bold")
    if sub: text(x + w/2, y + 40, sub, 11.5, "middle", fill=C["muted"])
def pin(x, y, label, side, nc=False):
    add(f'<circle cx="{x}" cy="{y}" r="3.6" fill="#fff" stroke="{C["nc"] if nc else C["edge"]}" stroke-width="1.6"/>')
    dx, anc = (9, "start") if side == "L" else (-9, "end")
    text(x + dx, y + 4.5, label, 12.5, anc, fill=C["nc"] if nc else C["text"])
    if nc:
        o = 14 if side == "R" else -14
        add(f'<path d="M{x+o-4},{y-4} l8,8 M{x+o-4},{y+4} l8,-8" stroke="{C["nc"]}" stroke-width="1.6"/>')
def wire(pts, color, width=2.6):
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>')

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(40, 38, "Touch panel wiring", 20, weight="bold")
text(40, 60, "Wire colours show the circuit, not the colour of wire to use. The tray is drawn from the back, to scale, as in tray.scad.", 12.5, fill=C["muted"])

# ---- the panel, back view -------------------------------------------------
# Matches tray.scad: each pad's wire comes through a hole near the pad's corner, runs
# down its column's channel on the underside, and along the trunk to the MPR121.
S = 40                      # px per inch
PX, PY = 120, 110           # panel's top-left corner, as seen from the back
def P(x, y): return (PX + x*S, PY + y*S)
add(f'<rect x="{PX}" y="{PY}" width="{12*S}" height="{15*S}" fill="{C["wood"]}" stroke="{C["edge"]}" stroke-width="1.6"/>')
text(PX + 6*S, PY - 12, "Tray, back view — 12 × 15 in", 14, "middle", "bold")

mm = 1/25.4
CW, CH, G = 4.0, 3.75, 0.25   # cell width and height, gap between pads, in inches
inset = 6*mm                  # hole from the pad's corner
trunk = 15 - 4.5*mm           # trunk centre line, from the top
tab_w, tab_h = 50*mm, 50*mm   # the tab that carries the boards, left of the panel from the back
for r in range(4):
    for b in range(3):          # b counts columns from the left as seen from the back
        ele = 3*r + (2 - b)     # electrodes are numbered left to right from the front
        x0, y0 = b*CW + G/2, r*CH + G/2
        x1, y1 = x0 + CW - G, y0 + CH - G
        (ax, ay), (bx_, by_) = P(x0, y0), P(x1, y1)
        add(f'<rect x="{ax}" y="{ay}" width="{bx_-ax}" height="{by_-ay}" fill="{C["pad"]}" stroke="{C["padedge"]}" stroke-width="1.2"/>')
        mx, my = P((x0 + x1)/2, (y0 + y1)/2)
        text(mx, my - 4, f"ELE{ele}", 15, "middle", "bold")
        text(mx, my + 14, "3.75 × 3.5 in", 11, "middle", fill=C["muted"])
        hx, hy = P(x0 + inset, y1 - inset)
        add(f'<circle cx="{hx}" cy="{hy}" r="3" fill="{C["lead"]}"/>')
for b in range(3):
    x = b*CW + G/2 + inset
    wire([P(x, G/2 + CH - G - inset), P(x, trunk)], C["lead"], 2)
wire([P(G/2 + inset, trunk), P(-29.5*mm, trunk)], C["lead"], 3.2)

# the tab with the MPR121 and the XIAO in pockets
bx0, by0 = P(-tab_w, 15 - tab_h)
add(f'<rect x="{bx0}" y="{by0}" width="{tab_w*S}" height="{tab_h*S}" fill="{C["wood"]}" '
    f'stroke="{C["edge"]}" stroke-width="1.6"/>')
for (x, y, w, h, name) in [(-46*mm, 15 - 22.55*mm, 33*mm, 19*mm, "MPR121"), (-51*mm, 15 - 45.5*mm, 21*mm, 17.5*mm, "XIAO")]:
    ax, ay = P(x, y)
    add(f'<rect x="{ax}" y="{ay}" width="{w*S}" height="{h*S}" fill="#ffffff" stroke="{C["edge"]}" stroke-width="1.2"/>')
    text(ax + w*S/2, ay + h*S/2 + 3.5, name, 8.5, "middle", "bold")

# ---- MPR121 to XIAO, schematic --------------------------------------------
MX, MY = 760, 110
board(MX, MY, 210, 520, "MPR121 breakout", "Adafruit 1982, address 0x5A")
XX, XY = 1100, 110
board(XX, XY, 200, 300, "XIAO ESP32-C3", "in its pocket, USB off the edge")

links = [("VIN", "3V3", C["v33"]), ("GND", "GND", C["gnd"]), ("SCL", "D5 · GPIO7", C["scl"]),
         ("SDA", "D4 · GPIO6", C["sda"]), ("IRQ", "D3 · GPIO5", C["irq"])]
for i, (m, x, col) in enumerate(links):
    y = MY + 80 + 40*i
    pin(MX + 210, y, m, "R"); pin(XX, y, x, "L")
    wire([(MX + 210, y), (XX, y)], col, 3)
y = MY + 80 + 40*5
pin(MX + 210, y, "3Vo", "R", nc=True)
pin(MX + 210, y + 40, "ADDR", "R", nc=True)

for i in range(12):
    y = MY + 70 + 37*i
    pin(MX, y, f"{i}", "L")
    wire([(MX - 70, y), (MX, y)], C["lead"], 1.8)
    text(MX - 76, y + 4.5, f"ELE{i} pad", 12, "end")
# The electrode row's 13th pin is GND, the same net as GND on the power row
# (Adafruit's Eagle file), so it is already grounded through the board.
pin(MX, MY + 70 + 37*12, "GND", "L", nc=True)
text(MX + 105, MY + 530 + 18, "Pin n goes to the pad labelled ELEn.", 11.5, "middle", fill=C["muted"], italic=True)

# notes and legend
add(f'<rect x="760" y="680" width="540" height="130" rx="8" fill="#fbfbfc" stroke="#e1e5e9"/>')
legend = [("3.3 V", C["v33"]), ("ground", C["gnd"]), ("SDA", C["sda"]), ("SCL", C["scl"]),
          ("IRQ", C["irq"]), ("pad lead", C["lead"])]
lx = 780
for name, col in legend:
    add(f'<path d="M{lx},{703} h22" stroke="{col}" stroke-width="3.4" stroke-linecap="round"/>'); text(lx+28, 707, name, 12)
    lx += 28 + 8*len(name) + 22
notes = ["Leads are 30 AWG. Each comes up through the hole at the dot, lies in the",
         "groove under its sticker, and runs in the underside channels to the MPR121.",
         "From the front, ELE0 is the top-left pad and the boards are bottom right.",
         "3Vo, ADDR and the GND beside ELE0 stay unconnected. The XIAO pins are from memory:",
         "check them against its silkscreen."]
for i, n in enumerate(notes): text(780, 732 + 17*i, n, 12, fill=C["muted"])
add("</svg>")
here = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(here, "..", "..", "docs", "wiring.svg")
open(dst, "w").write("\n".join(out))
print("wrote", os.path.normpath(dst))
