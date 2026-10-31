/* Joins a Wi-Fi network as a station and keeps rejoining if it drops. The network's
 * name and password are in wifi_secrets.h, which git ignores. */
#pragma once

/* Starts joining in the background. */
void wifi_start(void);

/* The network's name. */
const char *wifi_ssid(void);

/* The address the network gave the board, as text, or NULL while it is not connected. */
const char *wifi_address(void);
