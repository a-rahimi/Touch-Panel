/* Toggles a TP-Link Kasa smart plug or switch on the local network, over Kasa's local
 * protocol: JSON on UDP and TCP port 9999, obfuscated with an autokey XOR cipher. Older
 * Kasa firmware accepts it without a login; the HS103 here, on 1.1.3, does. */
#pragma once

#define KASA_ALIAS "office light" /* the name given to the switch in the Kasa app */

/* Starts the task that does the network work, so that callers never wait on it. */
void kasa_start(void);

/* Asks for the switch to be toggled, and returns at once. */
void kasa_toggle(void);

/* One line about the switch for the display: where it is and what last happened. */
const char *kasa_status(void);
