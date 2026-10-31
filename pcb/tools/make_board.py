"""Writes pcb/touch_panel.kicad_pcb from design.py. Run with KiCad's Python:

    ~/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
        pcb/tools/make_board.py

The board is the 12 x 15 inch pad grid with a strip below it for the electronics.
The front (the top layer) carries only the pads, top copper under solder mask, and every
part is on the back, so the front can lie flat against a desk. A via inside each pad's
corner takes its signal to the bottom layer, where it runs down one of the two vertical
gaps between pad columns, which together carry all 12 traces side by side in an order
chosen so that no two cross, and on along a bus to its 510 ohm resistor above the
module. The bottom layer under the pads is a hatched shield driven by GPIO14, whose
trace crosses the bus on the top layer. Everything below the grid is in a strip whose
copper is ground, starting 15 mm below the pads so ground does not take the field the
pads need. The module's antenna end is flush with the bottom edge. strip_router.py
routes the short connections in the strip.

Coordinates are as seen from the front. A part on the back is placed there and then
flipped left to right, which mirrors it, so the strip is laid out as the mirror image
of what it would be with the parts on the front.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402
import strip_router as router  # noqa: E402
from make_schematic import pin_names, uid  # noqa: E402

PCB = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(PCB, "touch_panel.kicad_pcb")
FP_DIR = os.path.expanduser("~/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")

MM = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


# Layout, in mm. The board's top-left corner is at (X0, Y0).
X0, Y0 = 20.0, 20.0
W = design.GRID_W
G = Y0 + design.GRID_H          # bottom edge of the pad grid
XM = X0 + W / 2                 # module centre
YM = G + 26.2
YB = YM + 12.8                  # bottom edge: the module's antenna end is flush with it
GND_TOP = G + 12                # where the strip's ground starts, 15 mm below the pads

TRACK, POWER_TRACK, CLEAR = 0.2, 0.25, 0.2
VIA_D, VIA_DRILL = 0.6, 0.3
MAX_HALF = POWER_TRACK / 2      # the widest track's half width, for clearances
POWER = {"VBUS", "+3V3"}
PITCH = 1.0                     # between the traces in a gap and in the bus

board = pcbnew.NewBoard(OUT)
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
nc = ds.m_NetSettings.GetDefaultNetclass()
nc.SetTrackWidth(MM(TRACK))
nc.SetClearance(MM(CLEAR))
nc.SetViaDiameter(MM(VIA_D))
nc.SetViaDrill(MM(VIA_DRILL))

NETS = {}
for name in sorted(design.nets()):
    NETS[name] = pcbnew.NETINFO_ITEM(board, name)
    board.Add(NETS[name])


def edge():
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(P(X0, Y0))
    s.SetEnd(P(X0 + W, YB))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.1))
    board.Add(s)


# ---- parts -----------------------------------------------------------------------

def placements():
    # the strip's parts, laid out as if on the front and then mirrored about the module,
    # because flipping them to the back mirrors them
    at = {"U1": (XM, YM, 180), "J1": (XM + 38, YB - 3.7, 0), "U3": (XM + 38, YB - 14, 0),
          "R15": (XM + 17, YM - 12, 0), "R16": (XM + 17, YM - 9.5, 0),
          "R13": (XM + 32, YB - 10, 90), "R14": (XM + 44, YB - 10, 90),
          "C1": (XM + 50, YB - 5, 0), "U2": (XM + 52, YB - 14, 0), "C2": (XM + 58, YB - 14, 90),
          "C3": (XM + 12.5, YM + 4, 90), "C4": (XM + 14.5, YM + 4, 90),
          "R17": (XM + 20, YM + 1, 90), "C5": (XM + 22, YM + 1, 90), "SW1": (XM + 70, YM + 4, 0),
          "R18": (XM - 14, YM - 8, 90), "SW2": (XM - 32, YM + 4, 0),
          "R19": (XM - 14, YM - 3, 90), "D1": (XM - 14, YM + 1, 90)}
    at = {ref: (2 * XM - x, y, rot) for ref, (x, y, rot) in at.items()}
    at["E13"] = (XM + 1.91, G - 1.5, 0)
    # Touch resistors, seen from the front: R6-R10 directly above the module pins they
    # connect to, R1-R5 left of the module, and R11-R12 right of the shield's path up from
    # GPIO14 (see ROW_ORDER in design.py).
    xs = [-13.34, -12.07, -10.80, -9.53, -8.26, -6.99, -4.45, -3.18, -1.91, -0.64, 3.18, 4.45]
    for i, dx in enumerate(xs):
        at[f"R{i + 1}"] = (XM + dx, YM - 16.5, 90)
    for e in range(12):
        c, r = e % design.COLS, e // design.COLS
        at[f"E{e + 1}"] = (X0 + (c + 0.5) * design.CELL_W, Y0 + (r + 0.5) * design.CELL_H, 0)
    holes = [(50.8, 95.25), (254.0, 95.25), (50.8, 285.75), (254.0, 285.75)]
    for i, (x, y) in enumerate(holes):
        at[f"H{i + 1}"] = (X0 + x, Y0 + y, 0)
    at["H5"] = (X0 + 8, (GND_TOP + YB) / 2, 0)
    at["H6"] = (X0 + W - 8, (GND_TOP + YB) / 2, 0)
    return at


def add_parts():
    at = placements()
    fps = {}
    for p in design.PARTS:
        lib, name = p["footprint"].split(":")
        path = os.path.join(PCB, "touch_panel.pretty") if lib == "touch_panel" else f"{FP_DIR}/{lib}.pretty"
        m = pcbnew.FootprintLoad(path, name)
        m.SetFPID(pcbnew.LIB_ID(lib, name))
        m.SetReference(p["ref"])
        m.SetValue(p["value"])
        if p["lcsc"]:
            m.SetField("LCSC", p["lcsc"])
            m.GetField("LCSC").SetVisible(False)  # for the BOM, not the silkscreen
        m.SetPath(pcbnew.KIID_PATH("/" + uid("sym", p["ref"])))
        m.SetSheetname("/")
        m.SetSheetfile("touch_panel.kicad_sch")
        x, y, rot = at[p["ref"]]
        m.SetPosition(P(x, y))
        m.SetOrientationDegrees(rot)
        if name.startswith("ESP32"):
            # The module footprint's ground pad carries 0.2 mm thermal vias, finer than
            # the 0.3 mm the board allows. At this module's power they are not needed,
            # so they become plain copper on the pad's side, inside the ground pad, and
            # the router gives the pad an ordinary via instead.
            for pad in m.Pads():
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and pcbnew.ToMM(pad.GetDrillSize().x) < 0.3:
                    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
                    pad.SetDrillSize(pcbnew.VECTOR2I(0, 0))
                    top = pcbnew.LSET()
                    top.AddLayer(pcbnew.F_Cu)
                    pad.SetLayerSet(top)
        if p["ref"].startswith(("R", "C")):
            m.Reference().SetVisible(False)  # 0402 and 0603 parts are too small to label legibly
        names = pin_names(p["symbol"])
        for pad in m.Pads():
            num = pad.GetNumber()
            if num not in p["pins"]:
                continue
            net = p["pins"][num]
            if net is None:
                # KiCad names an unconnected pin's net after its part, pin and pad
                net = f"unconnected-({p['ref']}-{names[num]}-Pad{num})"
                if net not in NETS:
                    NETS[net] = pcbnew.NETINFO_ITEM(board, net)
                    board.Add(NETS[net])
            pad.SetNet(NETS[net])
        board.Add(m)
        # every part but the pads and holes goes on the back; a footprint can only be
        # flipped once it is on the board
        if not p["ref"].startswith(("E", "H")) or name == "ShieldTap":
            m.Flip(m.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fps[p["ref"]] = m
    return fps


def pad_xy(fps, ref, num):
    for pad in fps[ref].Pads():
        if pad.GetNumber() == num:
            c = pad.GetPosition()
            return pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
    raise KeyError((ref, num))


# ---- copper ----------------------------------------------------------------------

def track(net, layer, a, b, width=TRACK):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(P(*a))
    t.SetEnd(P(*b))
    t.SetWidth(MM(width))
    t.SetLayer(layer)
    t.SetNet(NETS[net])
    board.Add(t)


def via(net, xy):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(*xy))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetWidth(MM(VIA_D))
    v.SetDrill(MM(VIA_DRILL))
    v.SetNet(NETS[net])
    board.Add(v)


def electrode_traces(fps):
    """Each pad's trace, all on the bottom layer after the via in its pad: down its gap,
    then along the bus to its resistor on the back. Lines in a gap are numbered 1-6 left
    to right; the order of pads in LEFT and RIGHT is what keeps them from crossing (see
    design.py)."""
    left = [(0, 3), (0, 2), (0, 1), (0, 0), (1, 0), (1, 1)]
    right = [(1, 3), (1, 2), (2, 0), (2, 1), (2, 2), (2, 3)]
    for side, cells, gap_x in (("L", left, X0 + design.CELL_W), ("R", right, X0 + 2 * design.CELL_W)):
        for k, (c, r) in enumerate(cells, start=1):
            net = f"ELE{r * design.COLS + c}"
            res = f"R{k}" if side == "L" else f"R{6 + k}"
            rx, ry = pad_xy(fps, res, "2")
            res_net = [pd.GetNetname() for pd in fps[res].Pads() if pd.GetNumber() == "2"][0]
            assert res_net == net, (res, res_net, net)
            line_x = gap_x + (k - 3.5) * PITCH
            row = 6 - k if side == "L" else k - 1
            bus_y = G + 2 + row * PITCH
            pad_bottom = Y0 + (r + 1) * design.CELL_H - design.GAP / 2
            pad_is_left = c * design.CELL_W + X0 < gap_x - 1
            vx = gap_x - design.GAP / 2 - 1.5 if pad_is_left else gap_x + design.GAP / 2 + 1.5
            vy = pad_bottom - 2.0
            via(net, (vx, vy))
            track(net, pcbnew.B_Cu, (vx, vy), (line_x, vy))
            track(net, pcbnew.B_Cu, (line_x, vy), (line_x, bus_y))
            track(net, pcbnew.B_Cu, (line_x, bus_y), (rx, bus_y))
            track(net, pcbnew.B_Cu, (rx, bus_y), (rx, ry))


def shield_trace(fps):
    """GPIO14 up to the shield tap: a short hop on the back, then the top layer over the
    bus, which is on the back, and down through a via into the tap."""
    px, py = pad_xy(fps, "U1", str(design.MODULE_PIN[design.SHIELD_GPIO]))
    tx, ty = pad_xy(fps, "E13", "1")
    up = py - 2.0
    track("SHIELD", pcbnew.B_Cu, (px, py), (px, up))
    via("SHIELD", (px, up))
    track("SHIELD", pcbnew.F_Cu, (px, up), (tx, ty))
    via("SHIELD", (tx, ty))


def usb_breakout(fps):
    """Breaks out the USB-C connector's middle pins, which are 0.5 mm apart, so the
    router only has to carry on from one point per net. Across the middle they run
    VBUS, (SBU), CC1, D-, D+, D-, D+, (SBU), CC2, VBUS, and the two D- pins and two D+
    pins interleave, so one pair must cross the other through vias.

    The connector is on the back, so its pads are on the bottom layer, and seen from the
    front it is mirrored: everything here is drawn as for a connector on the front and
    then mirrored (MIRROR), with the layers swapped. VBUS goes through a via above each
    of its pads to the top layer, and the two vias are joined there. That leaves room for
    CC1 and CC2 to swing out over the unused SBU pins and away to 2.8 mm either side of
    the middle. The data pins fan out inside them, the outer ones first, so no two
    tracks pass closer than 0.3 mm. D- then crosses D+: its two pins end in vias joined
    on the top layer, and D+ joins its pins on the bottom layer above them. Returns, for
    each net, the (layer, x, y) points to route on from."""
    MIRROR = -1
    pads = {pd.GetNumber(): pd for pd in fps["J1"].Pads()}
    mid = (pcbnew.ToMM(pads["A6"].GetPosition().x) + pcbnew.ToMM(pads["A7"].GetPosition().x)) / 2
    top = pcbnew.ToMM(pads["A6"].GetBoundingBox().GetY())

    def at(dx, dy):  # dx from the middle, before mirroring; dy above the pads' top edge
        return (mid + MIRROR * dx, top - dy)

    def path(net, num, pts):
        c = pads[num].GetPosition()
        pts = [(pcbnew.ToMM(c.x), pcbnew.ToMM(c.y))] + [at(*p) for p in pts]
        for a, b in zip(pts, pts[1:]):
            track(net, pcbnew.B_Cu, a, b)

    path("CC1", "A5", [(-1.25, 0.3), (-1.75, 0.8), (-1.75, 1.3), (-2.8, 2.35), (-2.8, 3.0)])
    path("CC2", "B5", [(1.75, 1.3), (2.8, 2.35), (2.8, 3.0)])
    path("USB_DN", "B7", [(-0.75, 1.6), (-1.6, 2.45), (-1.6, 3.0)])
    path("USB_DP", "A6", [(-0.25, 2.0), (-0.55, 2.3), (-0.55, 3.9)])
    path("USB_DN", "A7", [(0.25, 2.0), (0.55, 2.3), (0.55, 3.0)])
    path("USB_DP", "B6", [(0.75, 1.6), (1.6, 2.45), (1.6, 3.9)])
    path("VBUS", "A4", [(-2.45, 0.8)])
    path("VBUS", "A9", [(2.45, 0.8)])
    for x in (-2.45, 2.45):
        via("VBUS", at(x, 0.8))
    for x in (-1.6, 0.55):
        via("USB_DN", at(x, 3.0))
    track("VBUS", pcbnew.F_Cu, at(-2.45, 0.8), at(2.45, 0.8), POWER_TRACK)
    track("USB_DN", pcbnew.F_Cu, at(-1.6, 3.0), at(0.55, 3.0))
    track("USB_DP", pcbnew.B_Cu, at(-0.55, 3.9), at(1.6, 3.9))
    point = lambda layer, dx, dy: (layer, *at(dx, dy))  # layer 0 is the top, 1 the bottom
    return {"CC1": [point(1, -2.8, 3.0)], "CC2": [point(1, 2.8, 3.0)],
            "USB_DN": [point(0, -0.5, 3.0)], "USB_DP": [point(1, 0.5, 3.9)],
            "VBUS": [point(0, 0, 0.8)]}


def zone(net, layer, corners, hatch=False):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(NETS[net])
    z.SetLocalClearance(MM(CLEAR))
    z.SetMinThickness(MM(0.25))
    # solid connections to pads, because a thermal relief's spokes can be cut down to
    # one by nearby tracks, which a fab will not accept
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    if hatch:
        z.SetFillMode(pcbnew.ZONE_FILL_MODE_HATCH_PATTERN)
        z.SetHatchThickness(MM(0.5))
        z.SetHatchGap(MM(1.5))
    outline = z.Outline()
    outline.NewOutline()
    for x, y in corners:
        outline.Append(MM(x), MM(y))
    board.Add(z)


def keepout(corners):
    """No copper of any kind, on both layers."""
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetLayerSet(pcbnew.LSET.AllCuMask())
    for f in (z.SetDoNotAllowZoneFills, z.SetDoNotAllowTracks, z.SetDoNotAllowVias, z.SetDoNotAllowPads):
        f(True)
    z.SetDoNotAllowPads(False)       # a mounting hole is itself a pad
    z.SetDoNotAllowFootprints(False)
    outline = z.Outline()
    outline.NewOutline()
    for x, y in corners:
        outline.Append(MM(x), MM(y))
    board.Add(z)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def zones(fps):
    # the shield under the pad grid; it stops short of the bus band below the grid
    zone("SHIELD", pcbnew.B_Cu, rect(X0 + 0.5, Y0 + 0.5, X0 + W - 0.5, G), hatch=True)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone("GND", layer, rect(X0 + 0.5, GND_TOP, X0 + W - 0.5, YB - 0.5))
    # a square of bare board around each mounting hole, so no fill comes near the screw
    for ref in ("H1", "H2", "H3", "H4", "H5", "H6"):
        c = fps[ref].GetPosition()
        x, y = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
        keepout(rect(x - 3, y - 3, x + 3, y + 3))
    # and around the USB-C connector's plastic locating pegs, which the fill ignores
    for pad in fps["J1"].Pads():
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            c = pad.GetPosition()
            x, y = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
            r = pcbnew.ToMM(pad.GetDrillSize().x) / 2 + CLEAR + 0.1
            keepout(rect(x - r, y - r, x + r, y + r))


# ---- routing the strip -----------------------------------------------------------

# Clearance zones in the grid are grown by this much more than the rules need, because
# a diagonal track between cell centres can pass up to half a cell closer to copper.
SAFETY = 0.06
GROW = CLEAR + MAX_HALF + SAFETY


def route_strip(fps, starts):
    grid = router.Grid(XM - 80, G + 0.5, XM + 82, YB - 0.6, CLEAR, VIA_D)
    code = {name: i + 1 for i, name in enumerate(sorted(NETS))}
    layer_index = {pcbnew.F_Cu: 0, pcbnew.B_Cu: 1}
    mm = pcbnew.ToMM

    def pad_layers(pad):
        return [i for l, i in layer_index.items() if pad.IsOnLayer(l)]

    # everything already on the board is an obstacle, owned by its net
    for m in fps.values():
        for pad in m.Pads():
            net = code.get(pad.GetNetname(), router.BLOCKED)
            bb = pad.GetBoundingBox()
            grid.mark_rect(pad_layers(pad), mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()),
                           mm(bb.GetBottom()), net, GROW)
            if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_NPTH, pcbnew.PAD_ATTRIB_PTH):
                c = pad.GetPosition()
                grid.mark_disc([0, 1], mm(c.x), mm(c.y),
                               mm(max(pad.GetSize().x, pad.GetDrillSize().x)) / 2 + GROW, net)
    for t in board.GetTracks():
        net = code[t.GetNetname()]
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition()
            grid.mark_disc([0, 1], mm(c.x), mm(c.y), VIA_D / 2 + GROW, net)
            grid.add_via(*grid.cell(mm(c.x), mm(c.y)))
        else:
            s, e = t.GetStart(), t.GetEnd()
            grid.mark_segment(layer_index[t.GetLayer()], mm(s.x), mm(s.y), mm(e.x), mm(e.y), net,
                              mm(t.GetWidth()) / 2 + GROW)
    # A fine-pitch pad sits inside its neighbours' clearance zones, which would mark it
    # blocked even for its own net, so each pad's own copper goes back to its net.
    # Vias are placed against the occupancy from before this (see freeze_raw).
    grid.freeze_raw()
    for m in fps.values():
        for pad in m.Pads():
            if pad.GetNetname() in code:
                bb = pad.GetBoundingBox()
                grid.own_rect(pad_layers(pad), mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()),
                              mm(bb.GetBottom()), code[pad.GetNetname()])
    # the module's keepout around its antenna, where no copper may go
    for z in fps["U1"].Zones():
        bb = z.GetBoundingBox()
        grid.mark_rect([0, 1], mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom()),
                       router.BLOCKED, GROW)

    def cells(pad):
        c = pad.GetPosition()
        cx, cy = grid.cell(mm(c.x), mm(c.y))
        return [(i, cx, cy) for i in pad_layers(pad)]

    exact = {}  # a starting cell to the exact point it stands for, off the grid

    def lay(net, path, width):
        if path[0] in exact:
            # join the grid's first cell to the exact copper it was snapped from
            x, y = exact[path[0]]
            first = grid.xy(path[0][1], path[0][2])
            if math.dist((x, y), first) > 1e-3:
                track(net, pcbnew.F_Cu if path[0][0] == 0 else pcbnew.B_Cu, (x, y), first, width)
        for kind, *rest in router.to_segments(path):
            if kind == "via":
                xy = grid.xy(*rest[0])
                via(net, xy)
                grid.mark_disc([0, 1], xy[0], xy[1], VIA_D / 2 + GROW, code[net])
                grid.add_via(*rest[0])
            else:
                layer, a, b = rest
                pa, pb = grid.xy(*a), grid.xy(*b)
                track(net, pcbnew.F_Cu if layer == 0 else pcbnew.B_Cu, pa, pb, width)
                grid.mark_segment(layer, pa[0], pa[1], pb[0], pb[1], code[net], width / 2 + GROW)

    def net_pads(net):
        """Every pad of a net, each separately (a button has two pads numbered 1, which
        must both be wired), but pads stacked on one spot only once."""
        out, seen = [], set()
        for ref, num in design.nets()[net]:
            for pad in fps[ref].Pads():
                if pad.GetNumber() == num:
                    key = (pad.GetPosition().x, pad.GetPosition().y)
                    if key not in seen:
                        seen.add(key)
                        out.append((ref, pad))
        return out

    skip = {"GND", "SHIELD"} | {n for n in NETS if n.startswith("ELE")}
    routed = [n for n in design.nets() if n not in skip]

    def span(n):
        pts = [(mm(p.GetPosition().x), mm(p.GetPosition().y)) for _, p in net_pads(n)]
        return max(x for x, _ in pts) - min(x for x, _ in pts) + max(y for _, y in pts) - min(y for _, y in pts)

    # The USB-C connector's nets go first, while there is room around it; the rest go
    # shortest first.
    first = ["USB_DP", "USB_DN", "CC1", "CC2", "VBUS"]
    failed = []
    for net in sorted(routed, key=lambda n: (first.index(n) if n in first else len(first), span(n))):
        width = POWER_TRACK if net in POWER else TRACK
        pads = net_pads(net)
        if net in starts:
            # the connector's pins are already joined; carry on from the breakout
            tree = []
            for l, x, y in starts[net]:
                cell = (l, *grid.cell(x, y))
                exact[cell] = (x, y)
                tree.append(cell)
            todo = [p for r, p in pads if r != "J1"]
        else:
            tree = cells(pads[0][1])
            todo = [p for _, p in pads[1:]]
        while todo:
            # connect the pad nearest the copper so far
            tx = sum(c[1] for c in tree) / len(tree)
            ty = sum(c[2] for c in tree) / len(tree)
            todo.sort(key=lambda p: math.dist(cells(p)[0][1:], (tx, ty)))
            pad = todo.pop(0)
            targets = cells(pad)
            if set(targets) & set(tree):
                continue
            path = grid.route(tree, targets, code[net], MAX_HALF)
            if path is None:
                failed.append((net, pad.GetParentFootprint().GetReference(), pad.GetNumber()))
                if os.environ.get("DEBUG_GRID"):
                    c = pad.GetPosition()
                    grid.snapshot(f"/tmp/grid_{net}.ppm", mm(c.x) - 6, mm(c.y) - 8, mm(c.x) + 6, mm(c.y) + 4, code[net])
                continue
            lay(net, path, width)
            tree += path

    # every ground pad on only one layer gets a short track to a via to the other
    # layer's ground; pads on both layers and stacked pads need none
    for ref, pad in net_pads("GND"):
        (layer, cx, cy), *more = cells(pad)
        if more:
            continue
        spots = [(layer, cx + dx, cy + dy) for dy in range(-25, 26) for dx in range(-25, 26)
                 if grid.inside(cx + dx, cy + dy) and grid.free(layer, cx + dx, cy + dy, code["GND"])
                 and grid.via_fits(cx + dx, cy + dy, code["GND"], MAX_HALF)]
        path = grid.route([(layer, cx, cy)], spots, code["GND"], MAX_HALF, allow_via=False) if spots else None
        if path is None:
            failed.append(("GND", ref, pad.GetNumber()))
            continue
        lay("GND", path, POWER_TRACK)
        xy = grid.xy(path[-1][1], path[-1][2])
        via("GND", xy)
        grid.mark_disc([0, 1], xy[0], xy[1], VIA_D / 2 + GROW, code["GND"])
        grid.add_via(path[-1][1], path[-1][2])

    # stitch the two ground layers together every 5 mm wherever there is room
    step = int(5 / router.STEP)
    _, gy0 = grid.cell(0, GND_TOP + 1)
    for cy in range(gy0, grid.h - 5, step):
        for cx in range(5, grid.w - 5, step):
            if grid.via_fits(cx, cy, code["GND"], MAX_HALF):
                xy = grid.xy(cx, cy)
                via("GND", xy)
                grid.mark_disc([0, 1], xy[0], xy[1], VIA_D / 2 + GROW, code["GND"])
                grid.add_via(cx, cy)
    return failed


def labels():
    """Each pad's electrode number in the silkscreen, so the panel can be read from the front."""
    for e in range(12):
        c, r = e % design.COLS, e // design.COLS
        t = pcbnew.PCB_TEXT(board)
        t.SetText(f"ELE{e}")
        t.SetPosition(P(X0 + (c + 0.5) * design.CELL_W, Y0 + (r + 0.5) * design.CELL_H))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(MM(6), MM(6)))
        t.SetTextThickness(MM(0.8))
        board.Add(t)


def main():
    edge()
    fps = add_parts()
    electrode_traces(fps)
    shield_trace(fps)
    failed = route_strip(fps, usb_breakout(fps))
    labels()
    zones(fps)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(OUT, board)
    print("wrote", OUT, f"({W:.1f} x {YB - Y0:.1f} mm)")
    if failed:
        print("could not route:", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
