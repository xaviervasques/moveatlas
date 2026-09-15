"""Inventory the three CODY cohorts (cody_1, cody_2, cody_3) without modifying raw.

For every real data file (AppleDouble ._*, .DS_Store and .gitkeep are skipped) this:
  - classifies the MODALITY by inspecting the actual column header, not the path:
      * "coco_labels": COCO-17 keypoints (time + <kpt>_x/_y) + 8 phenomenology labels
                       (Dystonia, Tremor, Myoclonus, Chorea, Tics, Athetosis,
                        Ballismus, Stereotypie)
      * "sam3":        dense silhouette timeseries (contour_NNN_x/y + shape features)
      * "video":       raw external video (stays local; never enters processed/)
      * "unknown":     anything unrecognized (reported, not silently dropped)
  - extracts cohort / stage / rater (dd|lc|consensus) / exam condition
    (action|posture|rest) / external dataset / raw subject token
  - builds a leakage-safe NAMESPACED subject id, because external cohorts reuse
    P-numbers for different people and collide with the adult training ids.

Outputs (idempotent, overwrite):
  datasets/pose/cody_{1,2,3}/processed/manifest.csv   per-cohort file inventory
  datasets/pose/_cody_registry.csv                    global namespaced-subject registry

Env: atlas-mouvement (openpyxl). Usage: python build_cody_manifest.py
"""
import os
import re
import csv
import glob

REPO = os.path.dirname(os.path.abspath(__file__))
COHORTS = ["cody_1", "cody_2", "cody_3"]

LABELS = ["Dystonia", "Tremor", "Myoclonus", "Chorea", "Tics", "Athetosis",
          "Ballismus", "Stereotypie"]
VIDEO_EXT = {".mp4", ".wmv", ".mov"}


def is_noise(name):
    return name.startswith("._") or name in (".DS_Store", ".gitkeep")


def read_header(path):
    """Return the first-row column names of an xlsx cheaply (read-only)."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    header = []
    for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
        header = [str(c) for c in row if c is not None]
        break
    n_rows = ws.max_row  # best-effort; may be None in read-only
    wb.close()
    return header, n_rows


def classify(header):
    cols = set(header)
    if any(c.startswith("contour_") for c in cols) or "video_relpath" in cols:
        return "sam3"
    has_kpts = "nose_x" in cols and "left_ankle_y" in cols
    has_labels = sum(1 for L in LABELS if L in cols) >= 4
    if has_kpts and has_labels:
        return "coco_labels"
    if has_kpts:
        return "coco_pose"
    return "unknown"


def norm_subject(token):
    """p2 / P2 / C_3 / C3 -> ('P',2) canonical string 'P2'."""
    m = re.match(r"^([PpCc])_?0*(\d+)", token)
    if not m:
        return None
    return m.group(1).upper() + m.group(2)


def analyze_path(cohort, relpath):
    """Derive stage / rater / condition / external dataset / subject token from path."""
    parts = relpath.split(os.sep)
    low = [p.lower() for p in parts]
    rater = next((r for r in ("dataset_dd", "dataset_lc", "dataset_consensus")
                  if r in low), None)
    if rater:
        rater = rater.replace("dataset_", "")  # dd | lc | consensus
    condition = None
    for cond in ("action", "posture", "rest", "repos"):
        if any(cond in p for p in low):
            condition = "rest" if cond == "repos" else cond
            break
    ext_ds = next((p for p in low if re.fullmatch(r"dataset_[123]", p)), None)
    # stage = the top-level folder under raw/
    stage = parts[0] if parts else ""
    # subject token: look at filename first, then any P#/C# path component
    fname = os.path.splitext(parts[-1])[0]
    subj = norm_subject(fname)
    if subj is None:
        for p in parts:
            s = norm_subject(p)
            if s:
                subj = s
                break
    return stage, rater, condition, ext_ds, subj


def namespaced_id(cohort, stage, ext_ds, subj):
    """Leakage-safe id. Adult labeled training = one shared namespace across cohorts
    (same 25 people); external cohorts get their own namespace (different people who
    happen to reuse P-numbers)."""
    if subj is None:
        return None
    if ext_ds:  # external cohorts: namespace by dataset, these are distinct people
        return f"ext_{ext_ds.replace('dataset_', 'ds')}:{subj}"
    return f"adult:{subj}"  # the shared 25-subject adult labeled cohort


def main():
    global_rows = []
    for cohort in COHORTS:
        raw = os.path.join(REPO, "datasets", "pose", cohort, "raw")
        proc = os.path.join(REPO, "datasets", "pose", cohort, "processed")
        os.makedirs(proc, exist_ok=True)
        rows = []
        for path in glob.glob(os.path.join(raw, "**", "*"), recursive=True):
            if not os.path.isfile(path):
                continue
            name = os.path.basename(path)
            if is_noise(name):
                continue
            ext = os.path.splitext(name)[1].lower()
            rel = os.path.relpath(path, raw)
            stage, rater, cond, ext_ds, subj = analyze_path(cohort, rel)
            if ext in VIDEO_EXT:
                modality, header_n, nrows = "video", 0, 0
            elif ext == ".xlsx":
                try:
                    header, nrows = read_header(path)
                    modality = classify(header)
                    header_n = len(header)
                except Exception as e:
                    modality, header_n, nrows = f"error:{type(e).__name__}", 0, 0
            else:
                modality, header_n, nrows = f"other{ext}", 0, 0
            ns = namespaced_id(cohort, stage, ext_ds, subj)
            row = {
                "cohort": cohort, "stage": stage, "rater": rater or "",
                "condition": cond or "", "external_dataset": ext_ds or "",
                "subject_raw": subj or "", "subject_ns": ns or "",
                "modality": modality, "n_cols": header_n, "n_rows": nrows or "",
                "size_mb": round(os.path.getsize(path) / 1e6, 2),
                "relpath": rel,
            }
            rows.append(row)
            global_rows.append(row)
        # write per-cohort manifest
        cols = ["cohort", "stage", "rater", "condition", "external_dataset",
                "subject_raw", "subject_ns", "modality", "n_cols", "n_rows",
                "size_mb", "relpath"]
        with open(os.path.join(proc, "manifest.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: r["relpath"]))
        print(f"[{cohort}] {len(rows)} data files -> {cohort}/processed/manifest.csv")

    # global subject registry: which namespaced subjects exist, in which cohorts,
    # with which modalities, and where the adult redundancy lives.
    reg = {}
    for r in global_rows:
        ns = r["subject_ns"]
        if not ns:
            continue
        e = reg.setdefault(ns, {"cohorts": set(), "modalities": set(),
                                "stages": set(), "n_files": 0})
        e["cohorts"].add(r["cohort"])
        e["modalities"].add(r["modality"])
        e["stages"].add(f'{r["cohort"]}/{r["stage"]}')
        e["n_files"] += 1
    reg_path = os.path.join(REPO, "datasets", "pose", "_cody_registry.csv")
    with open(reg_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject_ns", "n_cohorts", "cohorts", "modalities",
                    "n_files", "canonical_source"])
        for ns in sorted(reg):
            e = reg[ns]
            # dedup rule: adults are canonical from cody_3; externals from cody_3 too
            canonical = "cody_3" if "cody_3" in e["cohorts"] else sorted(e["cohorts"])[0]
            w.writerow([ns, len(e["cohorts"]), "|".join(sorted(e["cohorts"])),
                        "|".join(sorted(e["modalities"])), e["n_files"], canonical])
    print(f"[registry] {len(reg)} namespaced subjects -> datasets/pose/_cody_registry.csv")


if __name__ == "__main__":
    main()
