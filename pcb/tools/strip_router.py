"""A small two-layer maze router for the electronics strip.

The routing area is a 0.1 mm grid on each copper layer. Every piece of copper already on
the board marks the cells around it as belonging to its net, out to the clearance plus
half a track width, so a track of another net centred on a free cell keeps its clearance.
A net is routed by A* from all of its copper so far to its next pad, moving in eight
directions on one layer or changing layer through a via, which costs much more than a
step. The result is turned back into straight track segments and vias.
"""
import heapq
import math

STEP = 0.1                      # mm per grid cell
DIAG = math.sqrt(2)
VIA_COST = 40                   # in steps, so a via is worth 4 mm of track
FREE, BLOCKED = 0, -1


class Grid:
    def __init__(self, x0, y0, x1, y1, clearance, via_d):
        self.x0, self.y0 = x0, y0
        self.w = int(round((x1 - x0) / STEP)) + 1
        self.h = int(round((y1 - y0) / STEP)) + 1
        self.clear = clearance
        self.via_r = via_d / 2
        # one signed int per cell and layer: FREE, BLOCKED, or the owning net's code + 1
        self.occ = [[FREE] * (self.w * self.h) for _ in range(2)]

    def cell(self, x, y):
        return int(round((x - self.x0) / STEP)), int(round((y - self.y0) / STEP))

    def xy(self, cx, cy):
        return self.x0 + cx * STEP, self.y0 + cy * STEP

    def inside(self, cx, cy):
        return 0 <= cx < self.w and 0 <= cy < self.h

    def _claim(self, layer, i, net):
        grids = [self.occ] + ([self.raw] if self.raw else [])
        for occ in grids:
            cur = occ[layer][i]
            if cur == FREE:
                occ[layer][i] = net
            elif cur != net:
                occ[layer][i] = BLOCKED

    raw = None

    def freeze_raw(self):
        """Keeps a copy of the occupancy before own_rect hands pads back to their nets.
        A track may leave a pad through cells that are within a neighbour's clearance,
        because it is narrower than the pad, but a via may not stand there, so via_fits
        checks this copy. Everything claimed afterwards is recorded in both."""
        self.raw = [list(layer) for layer in self.occ]

    def mark_rect(self, layers, x0, y0, x1, y1, net, grow):
        """Copper occupying a rectangle, with every cell whose centre is within grow of it
        claimed. Rounding to the nearest cell instead would reach half a cell too far,
        which at 0.5 mm pin pitch is enough to block a neighbouring pin's centre line."""
        ax = math.ceil((x0 - grow - self.x0) / STEP - 1e-9)
        bx = math.floor((x1 + grow - self.x0) / STEP + 1e-9)
        ay = math.ceil((y0 - grow - self.y0) / STEP - 1e-9)
        by = math.floor((y1 + grow - self.y0) / STEP + 1e-9)
        for cy in range(max(ay, 0), min(by, self.h - 1) + 1):
            gy = self.y0 + cy * STEP
            for cx in range(max(ax, 0), min(bx, self.w - 1) + 1):
                gx = self.x0 + cx * STEP
                # the corners are rounded, as clearance around a rectangle is
                dx = max(x0 - gx, 0, gx - x1)
                dy = max(y0 - gy, 0, gy - y1)
                if dx * dx + dy * dy <= grow * grow + 1e-9:
                    for layer in layers:
                        self._claim(layer, cy * self.w + cx, net)

    def own_rect(self, layers, x0, y0, x1, y1, net):
        """Gives the cells inside a pad to its own net, whatever claimed them before."""
        a, b = self.cell(x0, y0), self.cell(x1, y1)
        for cy in range(max(a[1], 0), min(b[1], self.h - 1) + 1):
            for cx in range(max(a[0], 0), min(b[0], self.w - 1) + 1):
                for layer in layers:
                    self.occ[layer][cy * self.w + cx] = net

    def mark_segment(self, layer, xa, ya, xb, yb, net, grow):
        """A track's centreline, with every cell within grow of it claimed."""
        n = max(1, int(math.hypot(xb - xa, yb - ya) / (STEP / 2)))
        r = int(math.ceil(grow / STEP))
        seen = set()
        for k in range(n + 1):
            x, y = xa + (xb - xa) * k / n, ya + (yb - ya) * k / n
            cx, cy = self.cell(x, y)
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    px, py = cx + dx, cy + dy
                    if (px, py) in seen or not self.inside(px, py):
                        continue
                    gx, gy = self.xy(px, py)
                    if _dist_seg(gx, gy, xa, ya, xb, yb) <= grow:
                        seen.add((px, py))
                        self._claim(layer, py * self.w + px, net)

    def mark_disc(self, layers, x, y, radius, net):
        cx, cy = self.cell(x, y)
        r = int(math.ceil(radius / STEP))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= (radius / STEP) ** 2 and self.inside(cx + dx, cy + dy):
                    for layer in layers:
                        self._claim(layer, (cy + dy) * self.w + cx + dx, net)

    def snapshot(self, path, x0, y0, x1, y1, net=None):
        """Writes a PPM image of a window of the grid, top layer on the left and bottom
        on the right: white free, black blocked, grey owned by some net, red owned by net."""
        a, b = self.cell(x0, y0), self.cell(x1, y1)
        w, h = b[0] - a[0], b[1] - a[1]
        rows = []
        for cy in range(a[1], b[1]):
            row = bytearray()
            for layer in (0, 1):
                for cx in range(a[0], b[0]):
                    v = self.occ[layer][cy * self.w + cx] if self.inside(cx, cy) else BLOCKED
                    row += (bytes((255, 255, 255)) if v == FREE else bytes((0, 0, 0)) if v == BLOCKED
                            else bytes((220, 40, 40)) if v == net else bytes((150, 150, 150)))
                row += bytes((0, 0, 255)) * 3
            rows.append(bytes(row))
        with open(path, "wb") as f:
            f.write(f"P6 {2 * w + 6} {h} 255\n".encode())
            f.write(b"".join(rows))

    def free(self, layer, cx, cy, net):
        v = self.occ[layer][cy * self.w + cx]
        return v == FREE or v == net

    def via_fits(self, cx, cy, net, track_half):
        # a via is wider than the track the cells were grown for, by via_r - track_half
        extra = int(math.ceil((self.via_r - track_half) / STEP))
        occ = self.raw or self.occ
        for dy in range(-extra, extra + 1):
            for dx in range(-extra, extra + 1):
                px, py = cx + dx, cy + dy
                if not self.inside(px, py):
                    return False
                i = py * self.w + px
                if any(occ[layer][i] not in (FREE, net) for layer in (0, 1)):
                    return False
        # and clear of every via already placed, holes being at least 0.25 mm apart
        return all((vx - cx) ** 2 + (vy - cy) ** 2 >= self.via_gap ** 2 for vx, vy in self.vias)

    vias = ()
    via_gap = 0

    def add_via(self, cx, cy):
        if not self.vias:
            self.vias = []
            self.via_gap = int(math.ceil((2 * self.via_r + 0.25) / STEP))
        self.vias.append((cx, cy))

    def route(self, sources, targets, net, track_half, allow_via=True, max_expand=3_000_000):
        """A* from any (layer, cx, cy) in sources to any in targets. Returns the cell path
        from a source to a target, or None."""
        targets = set(targets)
        if not targets:
            return None
        tx = [t[1] for t in targets]
        ty = [t[2] for t in targets]
        bx0, bx1, by0, by1 = min(tx), max(tx), min(ty), max(ty)

        def h(cx, cy):  # octile distance to the targets' bounding box
            dx = max(bx0 - cx, 0, cx - bx1)
            dy = max(by0 - cy, 0, cy - by1)
            return max(dx, dy) + (DIAG - 1) * min(dx, dy)

        dist, came, heap = {}, {}, []
        for s in sources:
            dist[s] = 0.0
            heapq.heappush(heap, (h(s[1], s[2]), 0.0, s))
        moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1),
                 (1, 1, DIAG), (1, -1, DIAG), (-1, 1, DIAG), (-1, -1, DIAG)]
        expanded = 0
        while heap:
            _, g, cur = heapq.heappop(heap)
            if g > dist.get(cur, math.inf):
                continue
            if cur in targets:
                path = [cur]
                while path[-1] in came:
                    path.append(came[path[-1]])
                return path[::-1]
            expanded += 1
            if expanded > max_expand:
                return None
            layer, cx, cy = cur
            steps = []
            for dx, dy, c in moves:
                nx, ny = cx + dx, cy + dy
                if self.inside(nx, ny) and self.free(layer, nx, ny, net):
                    # a diagonal step must not cut a blocked corner
                    if dx and dy and not (self.free(layer, cx + dx, cy, net) and self.free(layer, cx, cy + dy, net)):
                        continue
                    steps.append(((layer, nx, ny), c))
            if allow_via and self.via_fits(cx, cy, net, track_half):
                steps.append(((1 - layer, cx, cy), VIA_COST))
            for nxt, c in steps:
                ng = g + c
                if ng < dist.get(nxt, math.inf):
                    dist[nxt] = ng
                    came[nxt] = cur
                    heapq.heappush(heap, (ng + h(nxt[1], nxt[2]), ng, nxt))
        return None


def _dist_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def to_segments(path):
    """A cell path to [("track", layer, (cx, cy), (cx, cy)) | ("via", (cx, cy))], merging
    runs in one direction into one segment."""
    out = []
    start = path[0]
    prev = path[0]
    direction = None
    for cur in path[1:]:
        if cur[0] != prev[0]:  # layer change
            if (start[1], start[2]) != (prev[1], prev[2]):
                out.append(("track", prev[0], (start[1], start[2]), (prev[1], prev[2])))
            out.append(("via", (prev[1], prev[2])))
            start, direction = cur, None
        else:
            d = (cur[1] - prev[1], cur[2] - prev[2])
            if direction is not None and d != direction:
                out.append(("track", prev[0], (start[1], start[2]), (prev[1], prev[2])))
                start = prev
            direction = d
        prev = cur
    if (start[1], start[2]) != (prev[1], prev[2]):
        out.append(("track", prev[0], (start[1], start[2]), (prev[1], prev[2])))
    return out
