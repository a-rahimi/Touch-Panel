/* The 12 pads' readings, from whichever sensor the board has. CMake picks one by the
 * build target: the MPR121 on the XIAO ESP32-C3 (mpr121.c), or the ESP32-S3's own touch
 * inputs on the PCB (s3_touch.c). */
#pragma once
#include "esp_err.h"

#define SENSOR_PADS 12

/* "MPR121" or "ESP32-S3 touch", for the display. */
extern const char *const SENSOR_NAME;

esp_err_t sensor_init(void);

/* Each pad's reading, in electrode order (ELE0 first), oriented so that it rises as a
 * hand comes closer and scaled so that its noise is about one count. */
esp_err_t sensor_read(int level[SENSOR_PADS]);
