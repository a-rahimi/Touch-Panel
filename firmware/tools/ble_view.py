#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["bleak"]
# ///
"""Draw the dot's position, as the panel sends it over Bluetooth LE, in a window.

    ./ble_view.py           connect to the panel
    ./ble_view.py --demo    draw a simulated gesture instead, without Bluetooth

The window shows the panel from the front turned 180 degrees, like the grid on the USB
display, so ELE0 is at the bottom right. It is to scale, with the 12 pads. Each point fades
from red to the background over TRAIL_S seconds and is then dropped. Points less than
STROKE_GAP_S apart are joined into a stroke. Press q or Escape, or close the window, to
quit.
"""
import asyncio
import math
import queue
import sys
import threading
import time
import tkinter as tk

from bleak import BleakClient, BleakScanner

NAME = "Touch Panel"
POSITION = "d5bcb521-9543-4c3d-82d7-0b8cca71a30d"

TRAIL_S = 20.0 / 3   # seconds for a point to fade out
STROKE_GAP_S = 0.3
SCALE = 40              # pixels per inch
MARGIN = 30
PANEL = (12.0, 15.0)    # inches
CELL = (4.0, 3.75)
GAP = 0.25              # between pads
BACKGROUND = (250, 248, 243)
HOT = (220, 30, 30)


def colour(age):
    """Red when new, the background colour at TRAIL_S."""
    f = min(age / TRAIL_S, 1.0)
    rgb = [round(h + (b - h) * f) for h, b in zip(HOT, BACKGROUND)]
    return "#%02x%02x%02x" % tuple(rgb)


def px(x, y):
    """Window pixels for a point in panel inches, with the panel turned 180 degrees:
    flipped left to right, then top to bottom."""
    return MARGIN + (PANEL[0] - x) * SCALE, MARGIN + (PANEL[1] - y) * SCALE


class View:
    def __init__(self, points):
        self.points = points          # queue of (time, x, y) from the reader thread
        self.trail = []               # (time, x, y), oldest first
        self.status = "looking for " + NAME
        self.root = tk.Tk()
        self.root.title(NAME)
        for key in ("q", "<Escape>"):
            self.root.bind(key, lambda _: self.root.destroy())
        w, h = px(0, 0)
        self.canvas = tk.Canvas(self.root, width=w + MARGIN, height=h + MARGIN + 24,
                                background="#%02x%02x%02x" % BACKGROUND, highlightthickness=0)
        self.canvas.pack()
        self.draw_panel()
        self.root.after(33, self.tick)

    def draw_panel(self):
        c = self.canvas
        c.create_rectangle(*px(0, 0), *px(*PANEL), outline="#8a8172", width=2)
        for e in range(12):
            col, row = e % 3, e // 3
            x0, y0 = col * CELL[0] + GAP / 2, row * CELL[1] + GAP / 2
            (ax, ay), (bx, by) = px(x0, y0), px(x0 + CELL[0] - GAP, y0 + CELL[1] - GAP)
            c.create_rectangle(ax, ay, bx, by, fill="#f1dcb8", outline="#d2a86e")
            # the label goes at the pad's top left as drawn, whichever way it is turned
            c.create_text(min(ax, bx) + 0.3 * SCALE, min(ay, by) + 0.35 * SCALE, text=f"ELE{e}",
                          anchor="nw", fill="#9a7a50", font=("Helvetica", 12))
        self.status_text = c.create_text(MARGIN, px(0, 0)[1] + 14, anchor="w",
                                         fill="#555", font=("Helvetica", 12))

    def tick(self):
        now = time.time()
        while True:
            try:
                item = self.points.get_nowait()
            except queue.Empty:
                break
            if isinstance(item, str):
                self.status = item
            else:
                self.trail.append(item)
        self.trail = [p for p in self.trail if now - p[0] < TRAIL_S]

        c = self.canvas
        c.delete("trail")
        for a, b in zip(self.trail, self.trail[1:]):
            if b[0] - a[0] < STROKE_GAP_S:
                c.create_line(*px(a[1], a[2]), *px(b[1], b[2]), fill=colour(now - b[0]),
                              width=3, capstyle="round", tags="trail")
        for t, x, y in self.trail:
            cx, cy = px(x, y)
            r = 3
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=colour(now - t), outline="", tags="trail")
        if self.trail and now - self.trail[-1][0] < STROKE_GAP_S:
            cx, cy = px(*self.trail[-1][1:])
            c.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, outline="#c81e1e", width=3, tags="trail")
        c.itemconfigure(self.status_text, text=self.status)
        self.root.after(33, self.tick)


def read_ble(points):
    """Runs on a background thread: connects, and puts each position on the queue."""
    async def run():
        while True:
            device = await BleakScanner.find_device_by_name(NAME, timeout=10)
            if device is None:
                points.put(f"{NAME} not found; still looking")
                continue
            try:
                async with BleakClient(device) as client:
                    points.put(f"connected to {NAME}")

                    def on_position(_, data):
                        x, y, pad = data.decode().split(",")
                        points.put((time.time(), float(x), float(y)))
                        points.put(f"connected to {NAME}: " + (f"over ELE{pad}" if int(pad) >= 0 else "between pads"))

                    await client.start_notify(POSITION, on_position)
                    while client.is_connected:
                        await asyncio.sleep(0.5)
            except Exception as err:  # a dropped link or a busy device: try again
                points.put(f"connection lost ({err}); reconnecting")
            await asyncio.sleep(1)

    asyncio.run(run())


def demo(points):
    """A gesture over ELE2, 1, 0 and back every few seconds, for trying the window."""
    points.put("demo: simulated gesture, no Bluetooth")
    pads_x = [10, 6, 2, 6, 10]
    while True:
        for i in range(len(pads_x) - 1):
            for k in range(10):
                f = k / 10
                x = pads_x[i] + (pads_x[i + 1] - pads_x[i]) * f
                points.put((time.time(), x, 1.875 + 0.3 * math.sin(4 * x)))
                time.sleep(0.05)
        time.sleep(1.5)


def main():
    points = queue.Queue()
    source = demo if "--demo" in sys.argv[1:] else read_ble
    threading.Thread(target=source, args=(points,), daemon=True).start()
    View(points).root.mainloop()


if __name__ == "__main__":
    main()
