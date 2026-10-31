/* The MPR121 capacitive sensor, over I2C. */
#pragma once
#include <stdint.h>
#include "esp_err.h"

#define MPR121_ELECTRODES 12

/* Resets the chip, lets it choose each electrode's charge current and time, and
 * starts it measuring all 12 electrodes. */
esp_err_t mpr121_init(void);

/* The 10-bit filtered reading of each electrode. It falls as a hand comes closer,
 * because the extra capacitance takes longer to charge. */
esp_err_t mpr121_read(uint16_t filtered[MPR121_ELECTRODES]);
