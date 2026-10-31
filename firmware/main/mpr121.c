/* The MPR121 capacitive sensor over I2C, as the sensor of the XIAO ESP32-C3 build. */
#include "sensor.h"
#include "driver/i2c_master.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "pins.h"

/* Register addresses and start-up values are from my memory of NXP's datasheet and
 * Adafruit's library, not rechecked. */
#define ADDR 0x5A /* ADDR pin unconnected */

const char *const SENSOR_NAME = "MPR121";

#define REG_FILTERED 0x04 /* two bytes per electrode, little-endian, 10 bits */
#define REG_MHDR 0x2B     /* baseline filter, eleven registers from here */
#define REG_TOUCH_TH 0x41 /* then release threshold at +1, two per electrode */
#define REG_DEBOUNCE 0x5B
#define REG_CONFIG1 0x5C
#define REG_CONFIG2 0x5D
#define REG_ECR 0x5E
#define REG_AUTOCONFIG0 0x7B
#define REG_USL 0x7D
#define REG_LSL 0x7E
#define REG_TL 0x7F
#define REG_SOFTRESET 0x80

static i2c_master_dev_handle_t dev;

static esp_err_t write_reg(uint8_t reg, uint8_t v)
{
    uint8_t d[2] = {reg, v};
    return i2c_master_transmit(dev, d, sizeof d, 50);
}

/* Resets the chip, lets it choose each electrode's charge current and time, and
 * starts it measuring all 12 electrodes. */
esp_err_t sensor_init(void)
{
    i2c_master_bus_config_t bus_cfg = {
        .i2c_port = -1,
        .sda_io_num = PIN_SDA,
        .scl_io_num = PIN_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    i2c_master_bus_handle_t bus;
    ESP_ERROR_CHECK(i2c_new_master_bus(&bus_cfg, &bus));
    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = ADDR,
        .scl_speed_hz = 400000,
    };
    ESP_ERROR_CHECK(i2c_master_bus_add_device(bus, &dev_cfg, &dev));

    esp_err_t err = write_reg(REG_SOFTRESET, 0x63);
    if (err != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(2));
    write_reg(REG_ECR, 0x00); /* stopped, so the configuration can be written */

    /* Baseline filter: rising, falling and touched. The firmware keeps its own
     * baseline, so these only matter for the chip's touch flags. */
    static const uint8_t filter[11] = {0x01, 0x01, 0x0E, 0x00, 0x01, 0x05, 0x01, 0x00, 0x00, 0x00, 0x00};
    for (int i = 0; i < 11; i++) write_reg(REG_MHDR + i, filter[i]);
    for (int e = 0; e < SENSOR_PADS; e++) {
        write_reg(REG_TOUCH_TH + 2 * e, 12);
        write_reg(REG_TOUCH_TH + 2 * e + 1, 6);
    }
    write_reg(REG_DEBOUNCE, 0x00);
    write_reg(REG_CONFIG1, 0x10); /* 6 samples for the first filter, 16 uA charge current */
    write_reg(REG_CONFIG2, 0x20); /* 0.5 us charge time, 4 samples, 1 ms period */

    /* Auto-configuration picks each electrode's charge current and time so that its
     * reading lands between the limits below. They are for a 3.3 V supply. */
    write_reg(REG_USL, 200);
    write_reg(REG_TL, 180);
    write_reg(REG_LSL, 130);
    write_reg(REG_AUTOCONFIG0, 0x0B);

    /* Run all 12 electrodes, with the baseline loaded from the first reading. */
    return write_reg(REG_ECR, 0x8C);
}

/* The chip's 10-bit filtered reading falls as a hand comes closer, because the extra
 * capacitance takes longer to charge, so the level is 1023 minus it. */
esp_err_t sensor_read(int level[SENSOR_PADS])
{
    uint8_t reg = REG_FILTERED, d[2 * SENSOR_PADS];
    esp_err_t err = i2c_master_transmit_receive(dev, &reg, 1, d, sizeof d, 50);
    if (err != ESP_OK) return err;
    for (int e = 0; e < SENSOR_PADS; e++) level[e] = 1023 - ((d[2 * e] | d[2 * e + 1] << 8) & 0x3FF);
    return ESP_OK;
}
