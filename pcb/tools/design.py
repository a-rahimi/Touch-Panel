"""The touch panel's circuit: every part, its footprint and LCSC number, and the net on
each of its pins. make_schematic.py and make_board.py both read this, so the schematic
and the board cannot disagree.

An ESP32-S3-WROOM-1 module senses the 12 pads directly with its touch inputs, each
through a 510 ohm resistor at the module as Espressif's hardware design guidelines
recommend. GPIO14 (T14), the only touch pin that can drive a shield, drives a hatched
shield under the pads on the bottom layer. USB-C powers the board through a 3.3 V
regulator and carries the module's native USB for flashing and the serial console.
"""

# Panel geometry, in mm, shared with make_board.py. The pad grid is the tray's: 3 columns
# of 4 inches by 4 rows of 3.75 inches, with 1/4 inch gaps between pads.
INCH = 25.4
COLS, ROWS = 3, 4
CELL_W, CELL_H = 4 * INCH, 3.75 * INCH
GAP = 0.25 * INCH
GRID_W, GRID_H = COLS * CELL_W, ROWS * CELL_H

# Which touch input senses which pad. Electrodes are numbered as before: left to right
# and top to bottom seen from the front, so ELE0 is top left. The order is chosen so the
# traces from the pads reach their resistors without crossing (see make_board.py).
TOUCH = {9: 4, 6: 5, 3: 6, 0: 7, 1: 8, 4: 3,        # through the left channel
         10: 9, 7: 10, 2: 11, 5: 12, 8: 2, 11: 1}   # through the right channel
SHIELD_GPIO = 14

# GPIO number to ESP32-S3-WROOM-1 pin number, from KiCad's RF_Module symbol.
MODULE_PIN = {1: 39, 2: 38, 3: 15, 4: 4, 5: 5, 6: 6, 7: 7, 8: 12, 9: 17, 10: 18,
              11: 19, 12: 20, 13: 21, 14: 22, 0: 27, 48: 25}


def part(ref, symbol, footprint, value, lcsc, pins, **extra):
    return dict(ref=ref, symbol=symbol, footprint=footprint, value=value, lcsc=lcsc,
                pins=pins, **extra)


R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"


def module_pins():
    pins = {str(n): None for n in range(1, 42)}          # None: not connected
    pins.update({"1": "GND", "40": "GND", "41": "GND", "2": "+3V3", "3": "EN",
                 "13": "USB_DN_MCU", "14": "USB_DP_MCU", "27": "BOOT", "25": "LED"})
    for gpio in TOUCH.values():
        pins[str(MODULE_PIN[gpio])] = f"T{gpio}"
    pins[str(MODULE_PIN[SHIELD_GPIO])] = "SHIELD"
    return pins


PARTS = [
    part("U1", "RF_Module:ESP32-S3-WROOM-1", "RF_Module:ESP32-S3-WROOM-1",
         "ESP32-S3-WROOM-1-N8R2", "C2913204", module_pins()),
    part("U2", "Regulator_Linear:AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5",
         "AP2112K-3.3", "C51118", {"1": "VBUS", "2": "GND", "3": "VBUS", "4": None, "5": "+3V3"}),
    part("U3", "Power_Protection:USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
         "USBLC6-2SC6", "C7519",
         {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "5": "VBUS", "2": "GND"}),
    part("J1", "Connector:USB_C_Receptacle_USB2.0_16P",
         "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "USB-C", "C165948",
         {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
          "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
          "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
          "A8": None, "B8": None}),
    part("R13", "Device:R", R0402, "5.1k", "C25905", {"1": "CC1", "2": "GND"}),
    part("R14", "Device:R", R0402, "5.1k", "C25905", {"1": "CC2", "2": "GND"}),
    part("R15", "Device:R", R0402, "22", "C25092", {"1": "USB_DP", "2": "USB_DP_MCU"}),
    part("R16", "Device:R", R0402, "22", "C25092", {"1": "USB_DN", "2": "USB_DN_MCU"}),
    part("C1", "Device:C", C0603, "10u", "C19702", {"1": "VBUS", "2": "GND"}),
    part("C2", "Device:C", C0603, "10u", "C19702", {"1": "+3V3", "2": "GND"}),
    part("C3", "Device:C", C0603, "10u", "C19702", {"1": "+3V3", "2": "GND"}),
    part("C4", "Device:C", C0402, "100n", "C1525", {"1": "+3V3", "2": "GND"}),
    part("R17", "Device:R", R0402, "10k", "C25744", {"1": "+3V3", "2": "EN"}),
    part("C5", "Device:C", C0402, "1u", "C52923", {"1": "EN", "2": "GND"}),
    part("SW1", "Switch:SW_Push", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
         "RESET", "C318884", {"1": "EN", "2": "GND"}),
    part("R18", "Device:R", R0402, "10k", "C25744", {"1": "+3V3", "2": "BOOT"}),
    part("SW2", "Switch:SW_Push", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
         "BOOT", "C318884", {"1": "BOOT", "2": "GND"}),
    part("R19", "Device:R", R0402, "1k", "C11702", {"1": "LED", "2": "LED_A"}),
    part("D1", "Device:LED", "LED_SMD:LED_0603_1608Metric", "red", "C2286",
         {"1": "GND", "2": "LED_A"}),
]

# The touch resistors, numbered R1 to R12 left to right along the row above the module
# as seen from the front. The module is on the back, so seen from the front it is
# mirrored: GPIO4-8 come out on its left, GPIO3 and GPIO9-12 along its top, and GPIO1-2
# on its right, with GPIO14's shield trace between GPIO12 and GPIO2.
ROW_ORDER = [4, 5, 6, 7, 8, 3, 9, 10, 11, 12, 2, 1]
ELECTRODE_OF = {gpio: ele for ele, gpio in TOUCH.items()}
for i, gpio in enumerate(ROW_ORDER):
    PARTS.append(part(f"R{i + 1}", "Device:R", R0402, "510", "C25123",
                      {"1": f"T{gpio}", "2": f"ELE{ELECTRODE_OF[gpio]}"}))

# The pads themselves, and mounting holes, which are on the board but not in the BOM.
for e in range(COLS * ROWS):
    PARTS.append(part(f"E{e + 1}", "Connector:TestPoint", "touch_panel:Electrode",
                      f"ELE{e}", None, {"1": f"ELE{e}"}, electrode=e))
# The shield is a copper zone, so a small pad under it stands for it in the schematic.
PARTS.append(part("E13", "Connector:TestPoint", "touch_panel:ShieldTap", "SHIELD", None,
                  {"1": "SHIELD"}))
for i in range(6):
    PARTS.append(part(f"H{i + 1}", "Mechanical:MountingHole",
                      "MountingHole:MountingHole_3.2mm_M3", "M3", None, {}))


def nets():
    """Every net and the (ref, pin) pairs on it."""
    out = {}
    for p in PARTS:
        for pin, net in p["pins"].items():
            if net:
                out.setdefault(net, []).append((p["ref"], pin))
    return out


if __name__ == "__main__":
    for net, members in sorted(nets().items()):
        print(f"{net:12s} {' '.join(f'{r}.{p}' for r, p in members)}")
