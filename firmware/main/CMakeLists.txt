# The Wi-Fi network's name and password come from firmware/.env, which git ignores
# (.env.example shows the format). They are written into wifi_secrets.h in the build
# folder, so they never appear in the source.
idf_component_register(SRCS "main.c" "mpr121.c" "gesture.c" "wifi.c" "kasa.c" "ble.c"
                       PRIV_REQUIRES esp_driver_i2c esp_driver_usb_serial_jtag esp_wifi esp_netif
                                     esp_event nvs_flash lwip bt)

# ESP-IDF reads this file once early on only to learn the component's requirements,
# before the build folder exists, so the secrets are handled on the real pass only.
if(NOT CMAKE_BUILD_EARLY_EXPANSION)
    set(env "${CMAKE_CURRENT_LIST_DIR}/../.env")
    if(NOT EXISTS "${env}")
        message(FATAL_ERROR "Missing firmware/.env: copy firmware/.env.example to firmware/.env "
                            "and fill in the Wi-Fi network's name and password.")
    endif()
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${env}")
    file(STRINGS "${env}" lines)
    foreach(line ${lines})
        if(line MATCHES "^[ \t]*(WIFI_SSID|WIFI_PASSWORD)[ \t]*=(.*)$")
            set(key "${CMAKE_MATCH_1}")
            string(STRIP "${CMAKE_MATCH_2}" value)
            # surrounding quotes, single or double, are not part of the value
            string(REGEX REPLACE "^([\"'])(.*)\\1$" "\\2" value "${value}")
            # escaped for a C string literal
            string(REPLACE "\\" "\\\\" value "${value}")
            string(REPLACE "\"" "\\\"" value "${value}")
            set(${key} "${value}")
        endif()
    endforeach()
    foreach(key WIFI_SSID WIFI_PASSWORD)
        if("${${key}}" STREQUAL "")
            message(FATAL_ERROR "firmware/.env has no ${key}.")
        endif()
    endforeach()
    set(secrets "${CMAKE_CURRENT_BINARY_DIR}/wifi_secrets.h")
    file(WRITE "${secrets}.tmp" "/* Generated from firmware/.env by main/CMakeLists.txt. */\n"
                               "#define WIFI_SSID \"${WIFI_SSID}\"\n"
                               "#define WIFI_PASSWORD \"${WIFI_PASSWORD}\"\n")
    file(COPY_FILE "${secrets}.tmp" "${secrets}" ONLY_IF_DIFFERENT)
    file(REMOVE "${secrets}.tmp")
    target_include_directories(${COMPONENT_LIB} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
endif()
