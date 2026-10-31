#!/bin/bash
# Rebuilds the four tray tiles from cad/tray.scad and puts them on four plates of one
# Bambu Studio project, set up for a Bambu Lab X2D with a 0.4 nozzle in Bambu PLA
# Basic. The project carries no gcode: open cad/build/tray.3mf, pick a plate, and slice.
#
#   cad/tools/plate.sh          both stages
#   cad/tools/plate.sh stl      just the STLs, into cad/build/
#   cad/tools/plate.sh project  just the project, reusing the STLs in cad/build/
#
# Each tile gets a plate of its own, because the two narrow ones together are 253 mm
# wide and leave no room between them on the 256 mm bed. Every tile prints as drawn,
# top face up: the pockets and pad recesses open upward and the wire channels open
# onto the bed, so nothing needs support.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)     # cad/tools/
cad=$(cd "$here/.." && pwd)
scad=/Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD
bs=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
prof=/Applications/BambuStudio.app/Contents/Resources/profiles/BBL

machine="$prof/machine/Bambu Lab X2D 0.4 nozzle.json"
process="$prof/process/0.20mm Standard @BBL X2D.json"
filament="$prof/filament/Bambu PLA Basic @BBL X2D 0.4 nozzle.json"

tiles="tile_bl tile_br tile_tl tile_tr"
out="$cad/build"
project="$out/tray.3mf"

build_stls() {
    mkdir -p "$out"
    for p in $tiles; do
        echo "  $p.stl"
        "$scad" -o "$out/$p.stl" -D "part=\"$p\"" "$cad/tray.scad" 2>&1 \
            | grep -vE '^(ECHO|Compiling|Parsing|Geometr|CGAL|Total rendering|Fontconfig|   )' || true
    done
}

# --load-assemble-list makes each entry of "plates" a plate of the project. Every
# object needs "filaments", even on a single-material print.
write_list() {
    python3 - "$out" <<'PY'
import json, sys
r = sys.argv[1]
names = {"tile_bl": "Bottom left", "tile_br": "Bottom right, with the boards",
         "tile_tl": "Top left", "tile_tr": "Top right"}
print(json.dumps({"plates": [
    {"plate_name": label, "need_arrange": True,
     "objects": [{"path": f"{r}/{t}.stl", "count": 1, "filaments": [1]}]}
    for t, label in names.items()]}, indent=1))
PY
}

build_project() {
    mkdir -p "$out"
    local list; list=$(mktemp -t assemble-list)
    write_list > "$list"
    echo "  cad/build/tray.3mf"
    # A previous run left this read-only; see the chmod at the end.
    chmod u+w "$project" 2>/dev/null || true

    local log; log=$(mktemp -t bambu-log)
    "$bs" \
        --load-settings "$machine;$process" \
        --load-filaments "$filament" \
        --load-assemble-list "$list" \
        --ensure-on-bed \
        --export-3mf "$project" > "$log" 2>&1 || true

    # Bambu Studio writes a plausible project even when the run failed, so read the log.
    if grep -q "run found error" "$log"; then
        grep -iE "error" "$log" | sed 's/^/    /' >&2
        rm -f "$list" "$log"
        echo "  export failed; the project was not rebuilt" >&2
        exit 1
    fi
    rm -f "$list" "$log"

    # The CLI leaves the X2D's per-extruder printer settings empty or collapsed, and
    # an empty extruder_nozzle_stats stops the slicer finding either nozzle, so every
    # plate fails with "found slicing or export error". x2d-printer.json holds those
    # keys as Bambu Studio itself saved them for this printer.
    python3 "$here/patch-settings.py" "$project" "@$here/x2d-printer.json"

    python3 "$here/verify-project.py" "$project" enable_support=0 \
        'extruder_nozzle_stats=['"'"'Standard#1'"'"', '"'"'Standard#1'"'"']'

    # Read-only, because Bambu Studio writes an open project back to its path and would
    # silently replace this file. Use Save As to keep your own changes.
    chmod a-w "$project"
}

case "${1:-all}" in
    stl)     echo "building STLs";    build_stls ;;
    project) echo "building project"; build_project ;;
    all)     echo "building STLs";    build_stls
             echo "building project"; build_project ;;
    *)       echo "usage: $0 [stl|project|all]" >&2; exit 1 ;;
esac
echo "done"
