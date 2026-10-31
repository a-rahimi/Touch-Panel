# The Wi-Fi network's name and password are in main/wifi_secrets.h, which git ignores;
# main/wifi_secrets.h.example is the template.
if(NOT EXISTS "${CMAKE_CURRENT_LIST_DIR}/wifi_secrets.h")
    message(FATAL_ERROR "Missing firmware/main/wifi_secrets.h: copy wifi_secrets.h.example "
                        "to wifi_secrets.h and fill in the Wi-Fi network's name and password.")
endif()

# The sensor depends on the board: the XIAO ESP32-C3 reads an MPR121 over I2C, and the
# PCB's ESP32-S3 senses the pads with its own touch inputs (sensor.h).
if(IDF_TARGET STREQUAL "esp32s3")
    set(sensor "s3_touch.c")
    set(sensor_driver esp_driver_touch_sens esp_driver_gpio)
else()
    set(sensor "mpr121.c")
    set(sensor_driver esp_driver_i2c)
endif()

idf_component_register(SRCS "main.c" ${sensor} "gesture.c" "wifi.c" "kasa.c" "ble.c"
                       PRIV_REQUIRES ${sensor_driver} esp_driver_usb_serial_jtag esp_wifi esp_netif
                                     esp_event nvs_flash lwip bt)
