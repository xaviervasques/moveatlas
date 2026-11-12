# -*- coding: utf-8 -*-
"""Set fps and fps_provenance on records whose source states a frame rate that their
builder did not record, and fill the matching fps cells of the manifests.

Some sources state their rate only in a document (li_taati: the data paper states
30 frames per second; no file of the deposit carries it), and their builder wrote
fps None. This script patches the existing records in place instead of rebuilding
them, and verifies the container as written against the container as read:

- Records: every record of --source whose take starts with --take-prefix must have
  fps None, no fps_provenance and a unique (subject_ns, take); it gets fps (float)
  and fps_provenance (a sentence saying where the rate comes from). Every other
  record is copied unchanged.
- Manifests (each --manifest, csv with the columns source, subject_ns, take, fps,
  n_frames): each row of --source whose (subject_ns, take) is patched must be seen
  once per manifest, with an empty fps cell and the record's n_frames; its fps cell
  becomes str(fps) ('30.0'). The file keeps its line ending (read from the first
  line) and is re-serialized with csv.writer: the line count must be equal and
  exactly the patched lines may differ. Every patched record must be found in at
  least one manifest.
- Without --yes nothing is written (dry run: counts only). With --yes the container
  is written first (records.save, atomic through .part and os.replace), read back
  and checked: equal to the patched records, equal to the records as read once fps
  and fps_provenance are dropped, and every record outside the patched set keeps
  its fps. Only then are the manifests written. A failed check exits with
  'restore the backup'.
- Any refusal happens before the first write, so a refused run leaves every file
  untouched. A second run refuses (fps is no longer None).

--take-prefix restricts the patch to takes starting with it (remap_open turn_, the
fallback of the 2026-09 remap rebuild).

Usage: python set_stated_fps.py --container datasets/pose/li_taati/processed/canonical.npz
           --manifest datasets/_canonical_manifest.csv --source li_taati --fps 30
           --provenance "30 fps: ..." [--take-prefix PREFIX] [--yes]
Paths are relative to the repository (the folder of this script).
"""
import argparse
import csv
import io
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
from moveatlas import records  # noqa: E402

PATCHED = ("fps", "fps_provenance")
MANIFEST_COLUMNS = ("source", "subject_ns", "take", "fps", "n_frames")


def refuse(msg):
    raise SystemExit(f"set_stated_fps: refused: {msg}")


def _without(rec):
    return {k: v for k, v in rec.items() if k not in PATCHED}


def patch_records(old, source, prefix, fps, provenance):
    """The patched list and {(subject_ns, take): n_frames} of the patched records."""
    if not isinstance(old, list):
        refuse("the container holds a single record, not a list")
    new, want = [], {}
    for rec in old:
        if rec.get("source") != source or not str(rec.get("take", "")).startswith(prefix):
            new.append(rec)
            continue
        key = (rec["subject_ns"], rec["take"])
        if rec.get("fps") is not None:
            refuse(f"{key} already has fps {rec['fps']}")
        if "fps_provenance" in rec:
            refuse(f"{key} already has fps_provenance")
        if key in want:
            refuse(f"{key} occurs twice in the container")
        out = dict(rec)
        out["fps"] = fps
        out["fps_provenance"] = provenance
        want[key] = int(rec["n_frames"])
        new.append(out)
    if not want:
        refuse(f"no record of source {source!r} with a take starting with {prefix!r}")
    return new, want


def patch_manifest(path, source, want, fps):
    """(new text, number of rows set, line ending, keys found) for one manifest."""
    with open(path, encoding="utf-8", newline="") as f:
        txt = f.read()
    eol = "\r\n" if txt.split("\n", 1)[0].endswith("\r") else "\n"
    rows = list(csv.reader(io.StringIO(txt, newline="")))
    if not rows:
        refuse(f"{path} is empty")
    head = rows[0]
    missing = [c for c in MANIFEST_COLUMNS if c not in head]
    if missing:
        refuse(f"{path} lacks the columns {missing}")
    ci = {c: head.index(c) for c in MANIFEST_COLUMNS}
    seen = set()
    for r in rows[1:]:
        if not r or r[ci["source"]] != source:
            continue
        key = (r[ci["subject_ns"]], r[ci["take"]])
        if key not in want:
            continue
        if key in seen:
            refuse(f"{path}: {key} has two rows")
        seen.add(key)
        if r[ci["fps"]] != "":
            refuse(f"{path}: {key} has fps {r[ci['fps']]!r}, not empty")
        if int(r[ci["n_frames"]]) != want[key]:
            refuse(f"{path}: {key} has n_frames {r[ci['n_frames']]}, the record {want[key]}")
        r[ci["fps"]] = str(fps)
    buf = io.StringIO(newline="")
    csv.writer(buf, lineterminator=eol).writerows(rows)
    out = buf.getvalue()
    a, b = txt.split(eol), out.split(eol)
    if len(a) != len(b):
        refuse(f"{path}: the csv round trip changes the line count ({len(a)} -> {len(b)})")
    n_diff = sum(1 for x, y in zip(a, b) if x != y)
    if n_diff != len(seen):
        refuse(f"{path}: {n_diff} lines would change, {len(seen)} rows were set")
    return out, len(seen), eol, seen


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--container", required=True, help="relative to the repository")
    ap.add_argument("--manifest", action="append", required=True,
                    help="relative to the repository; repeatable")
    ap.add_argument("--source", required=True)
    ap.add_argument("--take-prefix", default="")
    ap.add_argument("--fps", type=float, required=True)
    ap.add_argument("--provenance", required=True)
    ap.add_argument("--yes", action="store_true", help="write (default: dry run)")
    a = ap.parse_args(argv)
    if not a.provenance.strip():
        refuse("--provenance is empty")
    if not a.fps > 0:
        refuse(f"--fps {a.fps} is not positive")

    cpath = os.path.join(REPO, a.container)
    old = records.load(cpath)
    new, want = patch_records(old, a.source, a.take_prefix, a.fps, a.provenance)
    print(f"{a.container}: {len(want)} of {len(old)} records of {a.source!r} "
          f"(take prefix {a.take_prefix!r}) get fps {a.fps} and fps_provenance")

    texts, found = [], set()
    for m in a.manifest:
        mpath = os.path.join(REPO, m)
        out, n, eol, seen = patch_manifest(mpath, a.source, want, a.fps)
        found |= seen
        texts.append((mpath, out))
        print(f"{m}: {n} manifest rows get fps {str(a.fps)!r} (line ending {eol!r})")
    lost = sorted(set(want) - found)
    if lost:
        refuse(f"{len(lost)} patched records have no manifest row, first {lost[:3]}")

    if not a.yes:
        print("dry run: nothing written (pass --yes to write)")
        return 0

    records.save(cpath, new)
    back = records.load(cpath)
    keys = set(want)
    kept = all(records.equal(b.get("fps"), o.get("fps"))
               for b, o in zip(back, old)
               if not (o.get("source") == a.source and (o.get("subject_ns"), o.get("take")) in keys))
    if not (records.equal(back, new)
            and records.equal([_without(r) for r in back], [_without(r) for r in old])
            and kept):
        raise SystemExit(f"set_stated_fps: {a.container} as written does not verify: "
                         "restore the backup; the manifests were not written")
    print(f"{a.container}: written and verified field by field against the records as read")
    for mpath, out in texts:
        with open(mpath, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        print(f"{os.path.relpath(mpath, REPO)}: written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
