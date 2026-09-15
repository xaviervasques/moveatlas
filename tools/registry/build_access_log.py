"""Build datasets/_access_log.csv: one row per ACCESS EVENT, append-only in spirit.

Design (idempotent):
  - datasets/_access_log_manual.csv  is HUMAN-OWNED. This script never rewrites it.
    It holds events only a person or a session can attest (DUA acceptances, denials,
    request emails, incident resolutions). Corrections are new rows with event=correction.
  - This script DERIVES the machine-establishable events (download_completed /
    download_failed / dataset_empty) from, in decreasing order of reliability:
      1. datasets/_download_log.csv and datasets/_*.log
      2. git history  -> the tree IS a git repository (checked at run time), but
         it is NOT usable to date arrivals: datasets/**/raw/ and processed/ are
         gitignored, so the only tracked file under a dataset folder is its
         datacard.md. Tried on 2026-08-22 and every dataset came back with the
         same date, namely the day the datacards were committed, not the day the
         data arrived. Git is therefore reported but NOT used for event_date.
      3. on-disk file timestamps (stat)  -> used for download_completed dates only
      4. KINEFM_HANDOFF_2.md section 6 (encoded as manual rows, not here)
  - Output datasets/_access_log.csv = manual rows + derived rows, sorted, deduplicated.

Anything not establishable from these sources is left "unknown". Dates are never
guessed; latency is never inferred from a file timestamp. The script prints how many
fields are unknown and why.

Env: atlas-mouvement. Usage: python build_access_log.py
"""
import os
import csv
import subprocess
import glob
import datetime
from collections import defaultdict

REPO = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(REPO, "datasets")
HAVE_GIT = None   # resolved in main()

def git_available(repo):
    try:
        r = subprocess.run(["git", "-C", repo, "rev-parse", "--git-dir"],
                           capture_output=True, text=True, timeout=20)
        return r.returncode == 0
    except Exception:
        return False


def git_first_seen(repo, relpath):
    """Date (YYYY-MM-DD) of the OLDEST commit touching relpath, or ''."""
    try:
        r = subprocess.run(
            ["git", "-C", repo, "log", "--diff-filter=A", "--follow",
             "--format=%ad", "--date=short", "--reverse", "--", relpath],
            capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().splitlines()[0].strip()
    except Exception:
        pass
    return ""


COLUMNS = ["dataset_id", "event_date", "event", "channel", "outcome",
           "latency_days", "requires_dua", "requires_account",
           "identifiable_media", "bytes_expected", "bytes_received",
           "note", "evidence"]

# _download_log.csv uses a few short names; map them to catalogue ids.
ALIAS = {
    "gaitpdb": "physionet_gaitpdb",
    "imu_inthewild": "imu_inthewild_iprognosis",
}

# catalogue 'acces' -> controlled channel vocabulary (original kept in note if needed)
CHANNEL = {
    "git": "direct_url", "direct": "direct_url", "zenodo": "direct_url",
    "physionet": "direct_url", "mendeley": "direct_url",
    "kaggle": "kaggle", "synapse": "synapse", "ieee": "ieee_dataport",
    "form": "google_form", "request": "email",
}

# Verifiable per-dataset attributes. Absent -> "unknown".
# identifiable_media: does the dataset as DISTRIBUTED contain face/full-body video.
IDENTIFIABLE = {
    # raw video distributed
    "koa_pd_nm": "yes", "modys_video": "yes", "gavd": "yes",
    "fog_turning_filho": "yes", "toronto_neuroface": "yes", "vidimu": "yes",
    "ntu_rgbd": "yes",
    # pose/params/IMU/aux -> not identifiable video
    "li_taati": "no", "care_pd": "no", "amass": "no", "capture24": "no",
    "pads": "no", "daphnet": "no", "kaggle_fog": "no", "physionet_gaitpdb": "no",
    "gaitndd": "no", "hd_accel_jnet": "no", "clinical_gait_multipatho": "no",
    "imu_inthewild_iprognosis": "no", "monipar": "no", "tremordb": "no",
    "gaitdb": "no", "alameda_tremor": "no", "fog_star": "no",
    "multimodal_fog": "no", "pd_biostamprc21": "no", "accel_fluctuations": "no",
    "weargait_pd": "no", "uci_parkinson_voix": "no", "kaggle_spiral": "no",
    "nqmitcsxpd": "no", "tappy_keystroke": "no",
    # genuinely uncertain -> unknown (omitted): park_fingertap, ataxie_kinect_dib,
    # motion_x, visionMD
}
REQUIRES_DUA = {
    "amass": "yes", "ntu_rgbd": "yes", "motion_x": "yes",
    "accel_fluctuations": "yes", "weargait_pd": "no",
}
REQUIRES_ACCOUNT = {
    "synapse": "yes", "ieee": "yes", "form": "yes", "kaggle": "yes",
    "git": "no", "direct": "no", "zenodo": "no", "physionet": "no",
    "mendeley": "no",
}

# Tools / bases that are NOT pathological public datasets: flagged so the paper
# denominator can exclude them (documented, task 6).
NOT_A_PUBLIC_DATASET = {"visionMD"}


def load_catalogue():
    rows = list(csv.DictReader(open(os.path.join(DS, "_catalogue.csv"))))
    return {r["jeu"]: r for r in rows}


def raw_dir(cat_row):
    d = os.path.join(DS, cat_row["dossier"], "raw")
    if not os.path.isdir(d):
        d = os.path.join(DS, cat_row["dossier"])
    return d


def max_mtime_date(folder):
    mts = []
    for f in glob.glob(folder + "/**/*", recursive=True):
        b = os.path.basename(f)
        if b.startswith("._") or not os.path.isfile(f):
            continue
        try:
            mts.append(os.path.getmtime(f))
        except OSError:
            pass
    if not mts:
        return None, 0
    return datetime.date.fromtimestamp(max(mts)).isoformat(), len(mts)


def aggregate_download_log():
    agg = defaultdict(lambda: {"ok": 0, "fail": 0, "bytes_ok": 0, "fails": set()})
    path = os.path.join(DS, "_download_log.csv")
    if not os.path.exists(path):
        return agg
    for r in csv.DictReader(open(path)):
        d = ALIAS.get(r["dataset"], r["dataset"])
        a = agg[d]
        st = (r.get("status") or "").strip()
        if st == "ok":
            a["ok"] += 1
            try:
                a["bytes_ok"] += int(r.get("bytes") or 0)
            except ValueError:
                pass
        else:
            a["fail"] += 1
            a["fails"].add(st)
    return agg


def row(**kw):
    r = {c: "" for c in COLUMNS}
    r.update(kw)
    return r


def main():
    global HAVE_GIT
    HAVE_GIT = git_available(REPO)
    cat = load_catalogue()
    dl = aggregate_download_log()
    log_mtime = ""
    dlp = os.path.join(DS, "_download_log.csv")
    if os.path.exists(dlp):
        log_mtime = datetime.date.fromtimestamp(os.path.getmtime(dlp)).isoformat()

    # load manual rows (never rewritten)
    manual = []
    mp = os.path.join(DS, "_access_log_manual.csv")
    if os.path.exists(mp):
        manual = list(csv.DictReader(open(mp)))
    manual_keys = {(m["dataset_id"], m["event_date"], m["event"]) for m in manual}

    derived = []
    unknown_counts = defaultdict(int)

    for jeu, c in cat.items():
        acces = c["acces"]
        channel = CHANNEL.get(acces, "other")
        ident = IDENTIFIABLE.get(jeu, "unknown")
        dua = REQUIRES_DUA.get(jeu, "unknown")
        acct = REQUIRES_ACCOUNT.get(acces, "unknown")
        for f in ("identifiable_media", "requires_dua", "requires_account"):
            if {"identifiable_media": ident, "requires_dua": dua,
                    "requires_account": acct}[f] == "unknown":
                unknown_counts[f] += 1

        common = dict(dataset_id=jeu, channel=channel,
                      requires_dua=dua, requires_account=acct,
                      identifiable_media=ident)
        a = dl.get(jeu)
        raw = raw_dir(c)
        mdate, nfiles = max_mtime_date(raw)
        # NOT used for event_date: see the module docstring. Only tracked file
        # under a dataset folder is its datacard, so this dates the datacard.
        gdate = ""

        # download_completed: obtained datasets (has files and/or ok rows in log)
        obtained = c["statut"] in ("traite", "telecharge_brut")
        if obtained and (a is None or a["ok"] > 0 or nfiles > 0):
            key = (jeu, gdate or mdate or "", "download_completed")
            if key not in manual_keys:
                date = mdate or ""
                src = "max on-disk mtime (stat)"
                derived.append(row(
                    event="download_completed", outcome="success",
                    event_date=date, latency_days="",
                    bytes_received=(a["bytes_ok"] if a else "") or "",
                    note=(f"date from {src}; {nfiles} raw files" +
                          ("" if date else "; NO date establishable")),
                    evidence=("derived:git" if gdate else "derived:stat")
                             + (";datasets/_download_log.csv" if a else ""),
                    **common))
            if not (gdate or mdate):
                unknown_counts["event_date"] += 1

        # download_failed: any FAIL rows in the download log
        if a and a["fail"] > 0:
            key = (jeu, log_mtime, "download_failed")
            if key not in manual_keys:
                derived.append(row(
                    event="download_failed", outcome="failure",
                    event_date=log_mtime,
                    note="curl failure code(s) " + ",".join(sorted(a["fails"])) +
                         "; date = _download_log.csv mtime (approx)",
                    evidence="datasets/_download_log.csv", **common))

        # gated / not-yet-obtained: outcome pending, date unknown (never guessed)
        if c["statut"] == "a_telecharger":
            key_present = any(m["dataset_id"] == jeu for m in manual)
            if not key_present:
                derived.append(row(
                    event="discovered", outcome="pending", event_date="",
                    note="gated, not yet obtained; no request date establishable "
                         "(unknown)",
                    evidence="derived:catalogue", **common))
                unknown_counts["event_date"] += 1

    # merge, sort (unknown dates last), write
    allrows = manual + derived
    allrows.sort(key=lambda r: (r["dataset_id"], r["event_date"] or "9999-99-99"))
    out = os.path.join(DS, "_access_log.csv")
    with open(out, "w", newline="") as f:
        # LF explicitly: DictWriter's \r\n default rewrote the whole file
        # on every rebuild and churned CRLF between the Mac and the PC
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in allrows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})

    print(f"wrote {out}: {len(allrows)} rows "
          f"({len(manual)} manual, {len(derived)} derived)")
    print("git history source: " + ("present but NOT usable for arrival dates "
                                   "(raw/ and processed/ are gitignored, only "
                                   "datacards are tracked)" if HAVE_GIT
                                   else "NOT AVAILABLE (not a git repository)"))
    print("unknown fields (why: not establishable from logs/stat/catalogue):")
    for k, v in sorted(unknown_counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
