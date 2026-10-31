# The Wi-Fi network's name and password are in main/wifi_secrets.h, which git ignores;
# main/wifi_secrets.h.example is the template.
if(NOT EXISTS "${CMAKE_CURRENT_LIST_DIR}/wifi_secrets.h")
    message(FATAL_ERROR "Missing firmware/main/wifi_secrets.h: copy wifi_secrets.h.example "
                        "to wifi_secrets.h and fill in the Wi-Fi network's name and password.")
endif()
idf_component_register(SRCS "main.c" "mpr121.c" "gesture.c" "wifi.c" "kasa.c" "ble.c"
                       PRIV_REQUIRES esp_driver_i2c esp_driver_usb_serial_jtag esp_wifi esp_netif
                                     esp_event nvs_flash lwip bt)
