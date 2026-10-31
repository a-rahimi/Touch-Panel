/* The ESP32-S3's own touch inputs as the sensor of the PCB build (pcb/).
 *
 * The S3 charges and discharges each pad between two voltages a fixed number of times
 * and counts how long that takes, so its reading rises with the pad's capacitance and
 * so with a hand coming closer. Pad ELEn is on touch channel Tn = GPIOn as wired in
 * pcb/tools/design.py. The shield under the pads is on T14 (GPIO14); SHIELD picks what
 * it does, which is one of the things this board exists to compare. */
#include "sensor.h"
#include "driver/gpio.h"
#include "driver/touch_sens.h"

const char *const SENSOR_NAME = "ESP32-S3 touch";

/* Touch channel (= GPIO) of each electrode, from TOUCH in pcb/tools/design.py. */
static const int channel_of[SENSOR_PADS] = {7, 8, 11, 6, 3, 12, 5, 10, 2, 4, 9, 1};

/* SHIELD_DRIVEN: T14 is driven with the waveform of the pad being measured, which
 *   hides the pads from what is behind the board without loading them.
 * SHIELD_GROUND: GPIO14 is driven low, which makes the shield a ground plane.
 * SHIELD_FLOAT: GPIO14 is an input, and the shield is left floating. */
enum { SHIELD_DRIVEN, SHIELD_GROUND, SHIELD_FLOAT };
#define SHIELD SHIELD_DRIVEN
#define SHIELD_DRIVE 7 /* untuned: 0-7, stronger for a shield with more capacitance */

/* untuned: charge/discharge cycles per measurement; more is slower and finer */
#define CHARGE_TIMES 500
/* untuned: raw counts per unit of the level main.c sees, chosen so that the noise is
 * about one unit, as with the MPR121; measure the raw noise and set this from it */
#define SCALE 16

static touch_sensor_handle_t sensor;
static touch_channel_handle_t chan[SENSOR_PADS];

esp_err_t sensor_init(void)
{
    touch_sensor_sample_config_t sample[TOUCH_SAMPLE_CFG_NUM] = {
        TOUCH_SENSOR_V2_DEFAULT_SAMPLE_CONFIG(CHARGE_TIMES, TOUCH_VOLT_LIM_L_0V5, TOUCH_VOLT_LIM_H_2V2)};
    touch_sensor_config_t cfg = TOUCH_SENSOR_DEFAULT_BASIC_CONFIG(1, sample);
    esp_err_t err = touch_sensor_new_controller(&cfg, &sensor);
    if (err != ESP_OK) return err;

    touch_channel_config_t ch = {
        .active_thresh = {2000}, /* the chip's own touch detection is not used */
        .charge_speed = TOUCH_CHARGE_SPEED_7,
        .init_charge_volt = TOUCH_INIT_CHARGE_VOLT_DEFAULT,
    };
    for (int e = 0; e < SENSOR_PADS; e++) {
        err = touch_sensor_new_channel(sensor, channel_of[e], &ch, &chan[e]);
        if (err != ESP_OK) return err;
    }

    if (SHIELD == SHIELD_DRIVEN) {
        touch_channel_handle_t shield;
        err = touch_sensor_new_channel(sensor, 14, &ch, &shield);
        if (err != ESP_OK) return err;
        touch_waterproof_config_t wp = {.guard_chan = NULL, .shield_chan = shield, .shield_drv = SHIELD_DRIVE};
        err = touch_sensor_config_waterproof(sensor, &wp);
        if (err != ESP_OK) return err;
    } else {
        gpio_config_t io = {.pin_bit_mask = 1ULL << 14,
                            .mode = SHIELD == SHIELD_GROUND ? GPIO_MODE_OUTPUT : GPIO_MODE_INPUT};
        gpio_config(&io);
        gpio_set_level(14, 0);
    }

    touch_sensor_filter_config_t filter = TOUCH_SENSOR_DEFAULT_FILTER_CONFIG();
    err = touch_sensor_config_filter(sensor, &filter);
    if (err != ESP_OK) return err;
    err = touch_sensor_enable(sensor);
    if (err != ESP_OK) return err;
    return touch_sensor_start_continuous_scanning(sensor);
}

esp_err_t sensor_read(int level[SENSOR_PADS])
{
    for (int e = 0; e < SENSOR_PADS; e++) {
        uint32_t smooth;
        esp_err_t err = touch_channel_read_data(chan[e], TOUCH_CHAN_DATA_TYPE_SMOOTH, &smooth);
        if (err != ESP_OK) return err;
        level[e] = (int)(smooth / SCALE);
    }
    return ESP_OK;
}
