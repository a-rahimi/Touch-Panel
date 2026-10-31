"""Read a finished Bambu Studio project back and check it says what it should.

Worth the seconds it costs: every failure mode hit while building this pipeline
has been a silent one, where a complete and plausible-looking project came out
carrying stock settings or missing an object from a plate.

Usage: verify-project.py project.3mf key=value [key=value ...]
Prints the plate contents, and exits non-zero naming anything that disagrees.
"""
import json, re, sys, zipfile

def main(path, pairs):
    want = dict(p.split("=", 1) for p in pairs)
    z = zipfile.ZipFile(path)

    settings = json.loads(z.read("Metadata/project_settings.config"))
    wrong = [(k, v, settings.get(k)) for k, v in want.items()
             if str(settings.get(k)) != v]

    model = z.read("Metadata/model_settings.config").decode()
    names = dict(re.findall(
        r'<object id="(\d+)">\s*<metadata key="name" value="([^"]+)"', model))
    placed, plates = set(), []
    for block in re.findall(r"<plate>.*?</plate>", model, re.S):
        plate = re.search(r'plater_name" value="([^"]*)', block).group(1)
        ids = re.findall(r'object_id" value="(\d+)"', block)
        placed |= set(ids)
        plates.append((plate, [names.get(i, i) for i in ids]))
    orphans = [n for i, n in names.items() if i not in placed]

    for plate, objs in plates:
        print(f"    {plate:<10} {', '.join(objs)}")
    for k, v, got in wrong:
        print(f"    WRONG: {k} is {got!r}, asked for {v!r}", file=sys.stderr)
    if orphans:
        print(f"    WRONG: on no plate: {', '.join(orphans)}", file=sys.stderr)
    if wrong or orphans:
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__.strip().splitlines()[-2])
    main(sys.argv[1], sys.argv[2:])
