"""Rewrite settings inside an exported Bambu Studio project.

Support has to be switched on after the export rather than during it. Enabled
while the project is being built it changes how the arranger packs: it stops
honouring the per-plate assignment from the assemble list and spills objects
onto later beds, which Bambu Studio reports as

    arrange failed: ap.name cap_1 ap.bed_idx 5, plate index 2

and then follows by writing a project with every override reverted to stock --
easy to miss, because it still exports a file and still names the custom
process. Patching afterwards is safe because the arrangement is already baked
into each object's transform, so nothing re-packs.

Usage: patch-settings.py project.3mf key=value [@block.json ...]

filament-setup.json in the repo root holds the two-filament configuration
lifted out of a project Bambu Studio itself saved. The CLI cannot write one:
it records both filament_settings_id entries but leaves 69 other filament_*
arrays with a single entry, so a generated project opens with one filament.
That file is the only copy of a working setup; it is not applied automatically.
"""
import json, shutil, sys, zipfile

SETTINGS = "Metadata/project_settings.config"

def main(path, pairs):
    changes = {}
    for item in pairs:
        if item.startswith("@"):          # @file.json merges a whole block
            changes.update(json.load(open(item[1:])))
        else:
            changes.update([item.split("=", 1)])
    with zipfile.ZipFile(path) as z:
        items = [(i.filename, z.read(i.filename)) for i in z.infolist()]
    if SETTINGS not in dict(items):
        sys.exit(f"{path} has no {SETTINGS}")
    out = []
    for name, data in items:
        if name == SETTINGS:
            d = json.loads(data)
            d.update(changes)
            data = json.dumps(d, indent=4).encode()
        out.append((name, data))
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in out:
            z.writestr(name, data)
    shutil.move(tmp, path)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__.strip().splitlines()[-1])
    main(sys.argv[1], sys.argv[2:])
