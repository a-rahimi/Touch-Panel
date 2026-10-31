#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["bleak", "pyobjc-framework-Cocoa"]
# ///
"""Speak the pad under the dot, through the Mac's speaker, each time it changes.

    ./ble_talker.py           listen to the panel over Bluetooth LE
    ./ble_talker.py --demo    speak a simulated gesture instead, without Bluetooth

The pad is the token in the panel's "x,y,pad" packets (firmware/main/ble.h). Between
pads (-1) is not spoken, so 2, between, 2 says "2" once. A number still being spoken is
cut off when the next one comes, so the speech keeps up with the hand. The speech comes
from macOS's synthesizer as a library (NSSpeechSynthesizer), which stays loaded and so
starts at once, rather than from a "say" process, which took about 0.35 s per number
here, longer than a hand stays on a pad. After the hand has been away for HAND_GONE_S,
the next pad is spoken even if it is the same one as before.
Stop with Ctrl-C.
"""
import asyncio
import sys
import time

from AppKit import NSSpeechSynthesizer

from bleak import BleakClient, BleakScanner

NAME = "Touch Panel"
POSITION = "d5bcb521-9543-4c3d-82d7-0b8cca71a30d"
HAND_GONE_S = 0.5
RATE = 200  # words per minute; say speaks at about 175-200 by default


class Talker:
    def __init__(self):
        self.last_pad = None
        self.last_seen = 0.0
        self.voice = NSSpeechSynthesizer.alloc().initWithVoice_(None)  # the system voice
        self.voice.setRate_(RATE)

    def speak(self, pad):
        self.voice.stopSpeaking()
        self.voice.startSpeakingString_(str(pad))

    def token(self, pad):
        now = time.time()
        if now - self.last_seen > HAND_GONE_S:
            self.last_pad = None
        self.last_seen = now
        if pad < 0 or pad == self.last_pad:
            return
        self.last_pad = pad
        print(f"pad {pad}", flush=True)
        self.speak(pad)


async def listen(talker):
    print(f"looking for {NAME}")
    device = await BleakScanner.find_device_by_name(NAME, timeout=15)
    if device is None:
        sys.exit(f"{NAME} not found; is the panel powered and not connected to something else?")
    async with BleakClient(device) as client:
        await client.start_notify(POSITION, lambda _, data: talker.token(int(data.decode().split(",")[2])))
        print("connected; move a hand over the panel")
        while client.is_connected:
            await asyncio.sleep(1)
    print("disconnected")


def demo(talker):
    """The recorded gesture, 2 - 1 - 0 . 0 - 1 - 2, at 20 frames a second."""
    frames = [2] * 6 + [-1] * 2 + [1] * 6 + [-1] * 2 + [0] * 6 + [None] * 6 + [0] * 6 + [-1] * 2 + [1] * 6 + [-1] * 2 + [2] * 6
    for f in frames:
        if f is not None:
            talker.token(f)
        time.sleep(0.05)
    time.sleep(1)


if __name__ == "__main__":
    t = Talker()
    try:
        if "--demo" in sys.argv[1:]:
            demo(t)
        else:
            asyncio.run(listen(t))
    except KeyboardInterrupt:
        pass
