#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["bleak"]
# ///
"""Print the dot's position as the panel sends it over Bluetooth LE. Stop with Ctrl-C.

    ./ble_monitor.py

Each line is "x,y,pad": x and y in inches from the panel's top-left corner seen from the
front, and the pad under the dot, or -1 between pads, as firmware/main/ble.h describes.
Nothing arrives while no hand is near the panel.
"""
import asyncio
import sys
import time

from bleak import BleakClient, BleakScanner

NAME = "Touch Panel"
POSITION = "d5bcb521-9543-4c3d-82d7-0b8cca71a30d"


async def main():
    print(f"looking for {NAME}")
    device = await BleakScanner.find_device_by_name(NAME, timeout=15)
    if device is None:
        sys.exit(f"{NAME} not found; is the panel powered and not connected to something else?")
    async with BleakClient(device) as client:
        start = time.time()

        def show(_, data):
            print(f"{time.time() - start:7.2f} s  {data.decode()}", flush=True)

        await client.start_notify(POSITION, show)
        print("connected; move a hand over the panel")
        while client.is_connected:
            await asyncio.sleep(1)
    print("disconnected")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
