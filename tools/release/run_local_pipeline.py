# -*- coding: utf-8 -*-
"""ONE-COMMAND local pipeline for MoveAtlas (written 2026-08-22, cloud session).

Run this ON A MACHINE WITH REAL NETWORK AND THE DISK (the iMac Terminal is fine:
    cd <external-volume>/KineFM && python3 run_local_pipeline.py --all
or on the tower:
    cd <backup-drive> && python run_local_pipeline.py --all
).

It chains, in order, everything the cloud session prepared and code-tested, and
SKIPS what is already done (idempotent; safe to re-run after an interruption):

  prep      unzip vidimu dataset.zip and tremordb.zip if needed (python zipfile)
  ingest    local ingestions, no network: multimodal_fog (+ its canonical EEG/EMG),
            vidimu, tremordb, pads, HPO movement map
  fetch     all no-account downloads with stable URLs (fetch_p2_lot.py entries
            of status direct/pattern), non-interactive; 'resolve' entries are
            LISTED at the end for a human to complete
  openneuro aws s3 sync of the small OpenNeuro sets (ds004584, ds007526);
            the big ones (ds004998 162 GB, ds005873 100s of GB) only with --big
  arrivals  ingest what fetch brought when possible (semg_walking via wfdb,
            cap_sleep EDF batch: the field verification of the EDF reader)
  validate  validate_canonical.py --full: every manifest row against the record
            it points at (structure, shape, NaN, units, subject identity)
  rebuild   build_catalogue.py, build_taxonomy_map.py, build_access_log.py
  git       git add -A + commit (native git: no lock problem here)

Options: --all (default) | --phases prep,ingest,... | --big | --dry
Log: _pipeline_log.txt (appended, timestamped). Each phase failure is caught,
reported, and the pipeline continues; the end summary lists failures.
Stdlib only for itself; child scripts need numpy (and wfdb for semg_walking:
the pipeline tries `pip install wfdb` once if missing).
"""
import argparse
import os
import subprocess
import sys
import time
import zipfile

REPO = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(REPO, "_pipeline_log.txt")
PY = sys.executable or "python3"
FAILS, DONE, SKIPPED = [], [], []

FETCH_AUTO = ["semg_walking", "cdystonia", "ltmm", "remap_open", "nhanes_accel",
              "clinvar_summary", "kamath_snpc_geo", "ixi_mri"]
# Still to resolve or still to pull. Removed 2026-08-22 once satisfied:
# cervical_motion, sixmwt_lifespan, ilg_ataxia_tables, chop_gma_features,
# panelapp_movement_panels, hubu_fis (all downloaded) and fog_star_2026 (proved
# byte-identical to fog_star, so it was never a separate dataset).
RESOLVE_LATER = ["gait120", "nonan_gaitprint", "gaitrec",
                 "stroke_gait_vancriekinge", "clinical_gait_2025",
                 "allen_human_microarray", "ninds_cde_motor"]
OPENNEURO_SMALL = [("ds004584", "datasets/eeg/pd_rest_eeg_ds004584/raw"),
                   ("ds007526", "datasets/eeg/pd_walking_eeg_ds007526/raw")]
OPENNEURO_BIG = [("ds004998", "datasets/eeg/pd_meg_stn_lfp_ds004998/raw"),
                 ("ds005873", "datasets/eeg/seizeit2/raw")]


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd, label, dry=False):
    log(f"RUN  {label}: {' '.join(cmd)}")
    if dry:
        return True
    try:
        r = subprocess.run(cmd, cwd=REPO)
        if r.returncode == 0:
            DONE.append(label)
            return True
        FAILS.append(f"{label} (exit {r.returncode})")
        log(f"FAIL {label} (exit {r.returncode}); continuing")
        return False
    except Exception as e:
        FAILS.append(f"{label} ({e})")
        log(f"FAIL {label}: {e}; continuing")
        return False


def exists(*rel):
    return os.path.exists(os.path.join(REPO, *rel))


def skip(label, why):
    SKIPPED.append(f"{label} ({why})")
    log(f"SKIP {label}: {why}")


def unzip_if_needed(zpath_rel, marker_rel, label, dry):
    if exists(*marker_rel):
        return skip(label, "already extracted")
    z = os.path.join(REPO, *zpath_rel)
    if not os.path.exists(z):
        return skip(label, "zip not on disk")
    log(f"RUN  {label}: unzip {z}")
    if dry:
        return
    try:
        with zipfile.ZipFile(z) as zf:
            zf.extractall(os.path.dirname(z))
        DONE.append(label)
    except Exception as e:
        FAILS.append(f"{label} ({e})")
        log(f"FAIL {label}: {e}")


def phase_prep(dry):
    unzip_if_needed(("datasets", "socle", "vidimu", "raw", "dataset.zip"),
                    ("datasets", "socle", "vidimu", "raw", "dataset"),
                    "unzip vidimu", dry)
    unzip_if_needed(("datasets", "imu", "tremordb", "raw", "tremordb.zip"),
                    ("datasets", "imu", "tremordb", "raw",
                     "effect-of-deep-brain-stimulation-on-parkinsonian-tremor-1.0.0"),
                    "unzip tremordb", dry)


def phase_ingest(dry):
    steps = [
        (["ingest_multimodal_fog.py"],
         ("datasets", "imu", "multimodal_fog", "processed", "streams_eeg_emg.pkl"),
         "ingest multimodal_fog"),
        (["build_canonical_eeg.py", "--only", "multimodal_fog"],
         ("datasets", "imu", "multimodal_fog", "processed", "canonical_eeg"),
         "canonical EEG (fog)"),
        (["build_canonical_emg.py", "--only", "multimodal_fog"],
         ("datasets", "imu", "multimodal_fog", "processed", "canonical_emg"),
         "canonical EMG (fog)"),
        (["ingest_vidimu.py"],
         ("datasets", "socle", "vidimu", "processed", "canonical.pkl"),
         "ingest vidimu"),
        (["ingest_tremordb.py"],
         ("datasets", "imu", "tremordb", "processed", "tremordb_velocity.pkl"),
         "ingest tremordb"),
        (["ingest_pads.py"],
         ("datasets", "imu", "pads", "processed", "canonical_imu.pkl"),
         "ingest pads"),
        (["build_hpo_movement_map.py"],
         ("docs", "hpo_movement_terms.csv"),
         "HPO movement map"),
    ]
    for script_args, marker, label in steps:
        if exists(*marker):
            skip(label, "output already present")
            continue
        if not exists(script_args[0]):
            skip(label, "script missing")
            continue
        run([PY] + script_args, label, dry)


def phase_fetch(dry):
    if not exists("fetch_p2_lot.py"):
        return skip("fetch", "fetch_p2_lot.py missing")
    run([PY, "fetch_p2_lot.py", "--only", ",".join(FETCH_AUTO)],
        "fetch (direct/pattern lot)", dry)
    run([PY, "fetch_p2_lot.py", "--only", "cap_sleep", "--cap-subset", "rbd,n"],
        "fetch cap_sleep rbd,n subset", dry)
    log("TODO (interactive): resolve-status downloads: "
        + ", ".join(RESOLVE_LATER)
        + "  -> python fetch_p2_lot.py --only <name> (paste the URL once; "
          "source pages are in the registry). LICENCE: cervical_motion and "
          "clinical_gait_2025 are CC BY 4.0; the CC BY-NC-ND once noted here "
          "was the ARTICLE licence, not the data (settled 2026-08-23).")


def have_aws():
    try:
        return subprocess.run(["aws", "--version"], capture_output=True).returncode == 0
    except Exception:
        return False


def phase_openneuro(dry, big):
    if not have_aws():
        return skip("openneuro", "aws CLI not installed (pip install awscli, "
                    "or use openneuro-py) - commands are in docs/TOWER_RUNBOOK.md")
    sets = OPENNEURO_SMALL + (OPENNEURO_BIG if big else [])
    if not big:
        log("openneuro: big sets (ds004998 162 GB, ds005873) skipped; re-run "
            "with --big to pull them")
    for acc, dest in sets:
        d = os.path.join(REPO, dest)
        os.makedirs(d, exist_ok=True)
        run(["aws", "s3", "sync", "--no-sign-request",
             f"s3://openneuro.org/{acc}", d], f"openneuro {acc}", dry)


def phase_arrivals(dry):
    semg_raw = os.path.join(REPO, "datasets", "emg", "physionet_semg_walking", "raw")
    if os.path.isdir(semg_raw) and any(f.endswith(".hea")
                                       for _, _, fs in os.walk(semg_raw) for f in fs):
        try:
            import wfdb  # noqa: F401
        except ImportError:
            run([PY, "-m", "pip", "install", "wfdb"], "pip install wfdb", dry)
        run([PY, "build_canonical_emg.py", "--only", "semg_walking"],
            "canonical EMG (semg_walking) FIRST-RUN VERIFICATION", dry)
    else:
        skip("semg_walking ingest", "no WFDB records under raw/ yet")
    cap_raw = os.path.join(REPO, "datasets", "eeg", "cap_sleep", "raw")
    if os.path.isdir(cap_raw) and any(f.lower().endswith((".edf", ".rec"))
                                      for _, _, fs in os.walk(cap_raw) for f in fs):
        run([PY, "build_canonical_eeg.py", "--only", "cap_sleep"],
            "canonical EEG (cap_sleep) FIRST-REAL-EDF VERIFICATION "
            "(review the UNRECOGNIZED column of the audit!)", dry)
    else:
        skip("cap_sleep ingest", "no EDF under raw/ yet")


def phase_validate(dry):
    """Cross-check every canonical manifest against the records it describes.
    Reports, never repairs. Non-zero exit is surfaced as a phase failure so a
    bad ingestion cannot slip through a green pipeline run unnoticed."""
    if not exists("validate_canonical.py"):
        return skip("validate_canonical.py", "missing")
    run([PY, "validate_canonical.py", "--full"], "validate_canonical.py --full", dry)


def phase_rebuild(dry):
    for script in ["build_catalogue.py", "build_taxonomy_map.py",
                   "build_access_log.py"]:
        if exists(script):
            run([PY, script], script, dry)
        else:
            skip(script, "missing")


def phase_git(dry):
    # "git add -A" was refused on Windows because datasets/aux/ carried a
    # reserved DOS device name that git could not hash, so the add failed
    # and could leave the index half-staged (docs/OPERATIONS.md s2). That
    # family became datasets/auxdata/ on 2026-09-11 and no corpus path is
    # reserved any more, so the refusal should be liftable - but it has
    # not been exercised on the PC since the rename, and a half-staged
    # index is expensive to unpick. It stays until a Windows session
    # confirms a clean `git add -A`, and then this block simply goes.
    if os.name == "nt":
        log("phase git: skipped on Windows (the datasets/aux reserved-name "
            "trap is gone since the auxdata rename, but this path is "
            "unverified there); stage and commit from macOS or Linux")
        return
    run(["git", "add", "-A"], "git add", dry)
    msg = "local pipeline run: downloads + ingestions + rebuilds"
    run(["git", "commit", "-m", msg], "git commit", dry)
    run(["git", "log", "--oneline", "-3"], "git log", dry)


PHASES = {"prep": lambda a: phase_prep(a.dry),
          "validate": lambda a: phase_validate(a.dry),
          "ingest": lambda a: phase_ingest(a.dry),
          "fetch": lambda a: phase_fetch(a.dry),
          "openneuro": lambda a: phase_openneuro(a.dry, a.big),
          "arrivals": lambda a: phase_arrivals(a.dry),
          "rebuild": lambda a: phase_rebuild(a.dry),
          "git": lambda a: phase_git(a.dry)}
ORDER = ["prep", "ingest", "fetch", "openneuro", "arrivals", "validate",
         "rebuild", "git"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--phases", default="",
                    help="comma list among: " + ",".join(ORDER))
    ap.add_argument("--big", action="store_true",
                    help="also pull the huge OpenNeuro sets")
    ap.add_argument("--dry", action="store_true", help="print, do nothing")
    args = ap.parse_args()
    todo = [p.strip() for p in args.phases.split(",") if p.strip()] or ORDER
    for p in todo:
        if p not in PHASES:
            raise SystemExit(f"unknown phase '{p}'; known: {', '.join(ORDER)}")
    log(f"=== pipeline start (phases: {', '.join(todo)}; dry={args.dry}) ===")
    for p in todo:
        log(f"--- phase {p} ---")
        PHASES[p](args)
    log("=== summary ===")
    log(f"done:    {len(DONE)}  | skipped: {len(SKIPPED)} | failed: {len(FAILS)}")
    for f in FAILS:
        log(f"  FAILED: {f}")
    if FAILS:
        log("re-run the same command after fixing; completed steps are skipped")
    log("remaining human items: resolve-status downloads (above), "
        "registrations and applications in datasets/PENDING_HUMAN.md, and "
        "emptying _to_delete/ (this script deletes nothing)")


if __name__ == "__main__":
    main()
