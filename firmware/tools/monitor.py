#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial"]
# ///
"""Show the touch panel's readings, as the firmware draws them.

    ./monitor.py

Each key is sent as soon as it is pressed, without Enter:

    b   take a new baseline, with hands away from the panel
    q   quit
"""
import glob
import select
import sys
import termios
import tty

import serial


def main():
    ports = glob.glob("/dev/cu.usbmodem*")
    if len(ports) != 1:
        sys.exit(f"expected exactly one /dev/cu.usbmodem* port, found {ports}")
    ser = serial.Serial(ports[0], 115200, timeout=0)
    print(__doc__.split("\n\n", 2)[2])

    old = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin)
    try:
        while True:
            ready, _, _ = select.select([sys.stdin, ser], [], [], 0.1)
            if ser in ready:
                sys.stdout.write(ser.read(4096).decode(errors="replace"))
                sys.stdout.flush()
            if sys.stdin in ready:
                key = sys.stdin.read(1)
                if key == "q":
                    break
                if key == "b":
                    ser.write(key.encode())
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        sys.stdout.write("\033[0m\033[?25h\n")  # the firmware hides the cursor


if __name__ == "__main__":
    main()
