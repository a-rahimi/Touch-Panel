/* Reports the centroid dot over Bluetooth LE. The board advertises as BLE_NAME with one
 * service, whose one characteristic notifies the dot while it is showing, as UTF-8 text
 * "x,y,pad": x and y are inches from the panel's top-left corner seen from the front,
 * with two decimals, and pad is the token the gesture matcher reads, the pad under the
 * dot or -1 between pads. Nothing is sent while the dot is not showing. */
#pragma once

#define BLE_NAME "Touch Panel"
#define BLE_SERVICE_UUID "d5bcb520-9543-4c3d-82d7-0b8cca71a30d"
#define BLE_POSITION_UUID "d5bcb521-9543-4c3d-82d7-0b8cca71a30d"

void ble_start(void);

/* Sends the dot to a connected central that has subscribed; otherwise does nothing. */
void ble_report(float x_in, float y_in, int pad);

/* "advertising", "connected" or "subscribed", for the display. */
const char *ble_state(void);
