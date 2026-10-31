#!/bin/bash
# Builds the firmware for one of the two boards, each in its own build folder so the two
# configurations never mix:
#
#   firmware/tools/build.sh xiao [flash]   the XIAO ESP32-C3 with the MPR121, into build/
#   firmware/tools/build.sh pcb [flash]    the ESP32-S3 PCB, into build-s3/
#
# Needs ESP-IDF v6 in ~/esp/esp-idf.
set -euo pipefail
cd "$(dirname "$0")/.."
. ~/esp/esp-idf/export.sh > /dev/null
case "${1:-}" in
    xiao) target=esp32c3; dir=build ;;
    pcb)  target=esp32s3; dir=build-s3 ;;
    *)    echo "usage: $0 xiao|pcb [flash]" >&2; exit 1 ;;
esac
shift
idf.py -B "$dir" -D SDKCONFIG="$dir/sdkconfig" -D IDF_TARGET="$target" build "$@"
