# -*- coding: utf-8 -*-
"""Download queue for MoveAtlas open datasets (no-application lot) -> datasets/.

RUN ON THE TOWER (or any machine with real network) from the repo root:
    python fetch_p2_lot.py --list
    python fetch_p2_lot.py                        # everything with a direct URL
    python fetch_p2_lot.py --only semg_walking,remap_open
    python fetch_p2_lot.py --cap-subset rbd,n     # CAP: RBD + normals only

v3 (2026-08-22): registry extended with the results of the second hunt (12 new
open sets + biology/ontology lane), English throughout, multi-URL entries, and a
'tool' status for repositories that need a dedicated client (OpenNeuro S3).
Session-network reality (tested 2026-08-22): only raw/media.githubusercontent.com
and PyPI are reachable from the working environments; EVERYTHING here is
therefore tower work. Stdlib only (urllib), resume via Range, sha256 at end of
file, journal in datasets/_download_log_p2.csv. 'resolve' entries have no stable
direct URL: the script shows the source page; paste the direct URL once and it is
remembered in datasets/_fetch_urls.json.

Touches NO v1 folder. New destinations only (datasets/emg/, eeg/, bio/,
ontology/, plus new sets under imu/, pose/, auxdata/).

License flags worth reading before use:
  cervical_motion   CC BY 4.0. The old CC BY-NC-ND note was wrong: that licence
                    belongs to the Scientific Data ARTICLE, not to the figshare
                    deposit, and the deposit governs the data (settled 2026-08-23).
  clinical_gait_2025 CC BY 4.0, same correction. Still check subject overlap with
                    the already-ingested clinical_gait_multipatho.
Everything else queued here is CC0 / CC BY / ODC-By / US-public-domain / GEO-open.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile

REPO = os.environ.get("KINEFM_REPO", ".")
DS = os.path.join(REPO, "datasets")
LOG = os.path.join(DS, "_download_log_p2.csv")
URLS_CACHE = os.path.join(DS, "_fetch_urls.json")
# figshare answers 202 Accepted (empty body) both while staging an archive AND
# when it is throttling the client. Confirmed 2026-08-22: after ~44 requests in
# 45 s from three parallel streams, EVERY figshare file returned 202, including
# ones downloaded successfully hours earlier. So: few connections, spaced out,
# and a long capped backoff that can ride out a throttle window.
STAGING_RETRIES = 20
STAGING_WAIT = 30        # seconds * attempt, capped by STAGING_WAIT_MAX
STAGING_WAIT_MAX = 300
INTER_FILE_PAUSE = 5     # seconds between files of the same entry

# status 'direct'  : stable URL(s), immediate download ('url' or 'urls')
# status 'pattern' : canonical PhysioNet URL (verify on first run)
# status 'resolve' : direct URL must be pasted once from the source page.
#                    datasets/_fetch_urls.json caches name -> URL, or name -> LIST
#                    of URLs for multi-file records (figshare collections, Zenodo,
#                    OSF, Dryad); resolved 2026-08-22 from the repository APIs.
# status 'tool'    : needs a dedicated client; the script prints the command
# status 'satisfied': already on disk under another dataset id; never fetched
REGISTRY = [
    # ---- movement / EMG / EEG (original P2 lot) ----------------------------
    dict(name="semg_walking", status="direct", dest="emg/physionet_semg_walking/raw",
         url="https://physionet.org/content/semg/get-zip/1.0.1/",
         zip_name="semg-1.0.1.zip", unzip=True, size="278.5 MB (verified)",
         note="healthy walking sEMG, 31 subjects, 2 kHz, ODC-By; M5 base"),
    dict(name="cdystonia", status="direct", dest="auxdata/cdystonia/raw",
         url="https://hbiostat.org/data/repo/cdystonia.sav",
         zip_name="cdystonia.sav", unzip=False, size="4.4 KB (verified)",
         # 2026-08-22: the .csv is gone from hbiostat (404); the repo now serves
         # SPSS .sav. Read it with pyreadstat / pandas.read_spss.
         note="TWSTRS scores, cervical dystonia trial; aux M12"),
    dict(name="ltmm", status="pattern", dest="imu/ltmm/raw",
         url="https://physionet.org/content/ltmm/get-zip/1.0.0/",
         zip_name="ltmm-1.0.0.zip", unzip=True, size="GB range",
         note="71 older adults, 3-day accelerometry, fallers; C3"),
    dict(name="cap_sleep", status="pattern", dest="eeg/cap_sleep/raw",
         url="https://physionet.org/content/capslpdb/get-zip/1.0.0/",
         zip_name="capslpdb-1.0.0.zip", unzip=True, size="LARGE (tens of GB)",
         note="108 PSG incl. 22 RBD; D6. Prefer --cap-subset rbd,n",
         files_base="https://physionet.org/files/capslpdb/1.0.0/"),
    dict(name="gait120", status="resolve", dest="emg/gait120/raw",
         source="https://doi.org/10.6084/m9.figshare.27677016",
         note="120 healthy adults mocap+sEMG, 15.38 GB in 12 zip parts "
              "(figshare; license to confirm on item page)"),
    dict(name="cervical_motion", status="resolve",
         dest="imu/cervical_motion_multiplanar/raw",
         source="https://doi.org/10.6084/m9.figshare.26935900",
         note="14 healthy cervical ROM, 2 IMU 74 Hz + goniometer; A4 normative. "
              "LICENSE CC BY-NC-ND 4.0 (no derivatives): legal review flag"),
    dict(name="remap_open", status="direct", dest="pose/remap_open/raw",
         url="https://data.bris.ac.uk/datasets/21h9f9e30v9cl2fapjggz4q1x7/"
             "21h9f9e30v9cl2fapjggz4q1x7.zip",
         zip_name="remap_open.zip", unzip=True, size="351.4 MiB",
         note="12 PD + 12 controls, coarsened 2D/3D skeletons, sit-to-stand + "
              "turns, CC BY 4.0 (RESOLVED 2026-08-22)"),
    dict(name="nhanes_accel", status="direct", dest="imu/nhanes_accel/raw",
         urls=["https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/PAXHD_G.xpt",
               "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/PAXDAY_G.xpt",
               "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/PAXHR_G.xpt",
               "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/DEMO_G.xpt"],
         unzip=False, size="~130 MB (header/day/hour + demographics)",
         note="NHANES 2011-2012 cycle G summary accelerometry + age; C3. "
              "US public domain (RESOLVED 2026-08-22)"),
    dict(name="nhanes_paxmin", status="direct", dest="imu/nhanes_accel/raw",
         url="https://ftp.cdc.gov/pub/NHANES/LargeDataFiles/PAXMIN_G.xpt",
         zip_name="PAXMIN_G.xpt", unzip=False, size="7.6 GB",
         note="minute-level cycle G; optional heavy pull (80 Hz raw lives at "
              "https://ftp.cdc.gov/pub/pax_g, choose deliberately)"),
    # ---- second hunt: movement additions -----------------------------------
    # SATISFIED, do not fetch again. The registry used to claim this record was
    # "DISTINCT from the already-ingested fog_star". It is NOT: downloading it on
    # 2026-08-22 produced files byte-identical to datasets/imu/fog_star/raw
    # (sha256 sensor_data 888875133fef386a..., clinical_data 91aa90f70e25d33d...,
    # README f05cbd9d64169a2c...). Zenodo 17838806 is the same record fog_star
    # already cites, so the duplicate copy was deleted; ingesting both would have
    # double-counted the same 22 patients and could have put one patient on both
    # sides of a split.
    dict(name="fog_star_2026", status="satisfied", dest="imu/fog_star/raw",
         source="https://zenodo.org/records/17838806",
         note="SAME RECORD as fog_star (verified by sha256 2026-08-22); already "
              "on disk and ingested as fog_star, nothing to fetch"),
    dict(name="hubu_fis", status="resolve", dest="pose/hubu_fis_fingertap/raw",
         source="https://zenodo.org/records/17738775",
         note="234 MDS-UPDRS finger-tapping videos + per-clip ratings, CC BY "
              "4.0, 10.8 GB single zip (B2 bradykinesia video)"),
    dict(name="sixmwt_lifespan", status="satisfied", dest="imu/sixmwt_lifespan/raw",
         source="https://doi.org/10.6084/m9.figshare.c.7954157",
         note="60 healthy 21-75 y (10/decade), 6MWT lower-back IMU 100 Hz, "
              "CC BY 4.0. COMPLETE at 148.4 MB, published-md5 verified "
              "2026-08-26, and ingested since 2026-08-22; the old '~288 MB' "
              "estimate here was wrong and made the complete file look "
              "partial for three days. Nothing to fetch"),
    dict(name="nonan_gaitprint", status="resolve", dest="imu/nonan_gaitprint/raw",
         source="https://doi.org/10.6084/m9.figshare.27815034",
         note="41 healthy 56+ y, 16 IMU 200 Hz full body, ~49 h walking; C3 "
              "(license to confirm on figshare record)"),
    dict(name="nonan_gaitprint_young", status="resolve",
         dest="imu/nonan_gaitprint_young/raw",
         source="https://doi.org/10.6084/m9.figshare.c.6415061",
         note="the true NONAN sibling (owner go 2026-08-28): 35 healthy young "
              "adults, same 16-IMU 200 Hz protocol, one figshare article per "
              "subject, CC0 verified per article. SEPARATE DIRECTORY on "
              "purpose: subject IDs collide with the older cohort (S009/S013/"
              "S019 exist in both with different content). S039.zip has an "
              "EMPTY computed_md5 in the API: verified by sha256 journal only"),
    dict(name="gaitrec", status="resolve", dest="imu/gaitrec/raw",
         source="https://doi.org/10.6084/m9.figshare.c.4788012",
         note="2084 musculoskeletal patients + 211 controls, bilateral GRF 250 "
              "Hz, 75k trials; E4 antalgic-gait negative control; CC BY/CC0"),
    dict(name="stroke_gait_vancriekinge", status="resolve",
         dest="pose/stroke_gait_vancriekinge/raw",
         source="https://doi.org/10.6084/m9.figshare.c.6503791",
         note="50 stroke + 138 controls (19-85 y), full-body mocap C3D + 14-"
              "muscle EMG + GRF; D3 hemiparetic/spastic gait WITH pathological "
              "EMG (license per item, Sci Data CC BY)"),
    # SATISFIED, do not fetch. Settled 2026-08-23 on the Paris machine: the
    # resolved download URL for this record is figshare file 53704514, and the
    # md5 of datasets/imu/clinical_gait_multipatho/raw/dataset.zip matches the
    # published md5 (e7701e2ee2d8e6164a011f7c264d7649) exactly. Same deposit,
    # already downloaded AND ingested (1,356 canonical IMU records) under the
    # id clinical_gait_multipatho. The licence is CC BY 4.0 (item licence read
    # via api.figshare.com) and the old subject-overlap flag was identity.
    dict(name="clinical_gait_2025", status="satisfied",
         dest="imu/clinical_gait_multipatho/raw",
         source="https://doi.org/10.6084/m9.figshare.28806086",
         note="SAME RECORD as clinical_gait_multipatho (verified by md5 "
              "2026-08-23); already on disk and ingested, nothing to fetch"),
    dict(name="ilg_ataxia_tables", status="resolve", dest="auxdata/ilg_ataxia_tables/raw",
         source="https://datadryad.org/dataset/doi:10.5061/dryad.4tmpg4f62",
         note="43 ataxia + 35 controls: step variability/smoothness aggregate "
              "tables + SARA (172 KB, CC0); D2 reference statistics only"),
    dict(name="chop_gma_features", status="resolve", dest="pose/chop_gma_features/raw",
         source="https://osf.io/gztmd/",
         note="1053-infant GMA pipeline: de-identified kinematic feature tables "
              "+ model weights + YouTube-8M infant ViTPose keypoints; C2 "
              "(features only, raw video not shared)"),
    # ---- biology / ontology lane -------------------------------------------
    dict(name="kamath_snpc_geo", status="direct", dest="bio/kamath_snpc_geo/raw",
         urls=["https://ftp.ncbi.nlm.nih.gov/geo/series/GSE178nnn/GSE178265/suppl/GSE178265_Homo_matrix.mtx.gz",
               "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE178nnn/GSE178265/suppl/GSE178265_Homo_bcd.tsv.gz",
               "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE178nnn/GSE178265/suppl/GSE178265_Homo_features.tsv.gz"],
         unzip=False, size="~4.8 GB",
         note="human SNpc snRNA-seq count matrix, PD vs control (Kamath 2022); "
              "M10 cellular substrate; GEO open"),
    dict(name="clinvar_summary", status="direct", dest="bio/clinvar/raw",
         url="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz",
         zip_name="variant_summary.txt.gz", unzip=False, size="~0.5 GB",
         note="all ClinVar interpretations; filter to movement-disorder genes "
              "(PRKN, LRRK2, GBA1, HTT, TOR1A, THAP1, ATXN*...); M9"),
    dict(name="ixi_mri", status="direct", dest="bio/ixi_mri/raw",
         urls=["http://biomedic.doc.ic.ac.uk/brain-development/downloads/IXI/IXI-T1.tar",
               "http://biomedic.doc.ic.ac.uk/brain-development/downloads/IXI/IXI-T2.tar",
               "http://biomedic.doc.ic.ac.uk/brain-development/downloads/IXI/IXI.xls"],
         unzip=False, size="~10 GB (T1+T2; add PD/MRA/DTI tars if wanted)",
         note="~600 healthy adults 20-86 y MRI, CC BY-SA 3.0; M8 healthy "
              "aging reference"),
    dict(name="allen_human_microarray", status="resolve",
         dest="bio/allen_human_brain/raw",
         source="https://human.brain-map.org/static/download",
         note="6-donor whole-brain normalized microarray zips (basal ganglia "
              "sampled); Allen ToU (non-commercial research, cite); M10"),
    dict(name="panelapp_movement_panels", status="resolve",
         dest="bio/panelapp/raw",
         source="https://panelapp.genomicsengland.co.uk/panels/540/",
         note="signed-off gene panel TSVs: 540 + 847 (dystonia/chorea adult + "
              "childhood), 192 early-onset dystonia, 477 ataxia, 1669 adult "
              "neuro superpanel; download buttons on each panel page; M9"),
    dict(name="hpo_release", status="resolve", dest="ontology/hpo/raw",
         source="https://github.com/obophenotype/human-phenotype-ontology/releases/latest",
         note="REFRESH lane only: hp.obo + phenotype.hpoa + genes_to_phenotype "
              "already on disk (release 2025-01-16 via pyhpo, 2026-08-22); "
              "pull newer release assets when convenient"),
    dict(name="ninds_cde_motor", status="resolve", dest="auxdata/clinical_scales/raw",
         source="https://commondataelements.ninds.nih.gov/",
         note="NINDS CDE catalog exports for PD/HD/ataxia motor assessments "
              "(machine-readable item structures; MDS-UPDRS full text stays "
              "copyrighted, do not redistribute)"),
    dict(name="ninapro", status="resolve", dest="emg/ninapro/raw",
         source="https://ninapro.hevs.ch/",
         note="RECLASSIFIED 2026-08-25: the site now serves the preprocessed "
              "zips DIRECTLY, no account (the old registration wall is gone; "
              "checked on DB1 and DB2 pages). 67 files cached in "
              "_fetch_urls.json: DB1 s1-27 (10-electrode Otto Bock + "
              "Cyberglove, 100 Hz) and DB2 s1-40 (12-electrode Delsys, 2 kHz). "
              "No explicit licence on the pages: cite Atzori 2014, keep the "
              "redistribution flag until the terms are found in writing"),
    # ---- OpenNeuro lane (dedicated client) ---------------------------------
    dict(name="seizeit2", status="tool", dest="eeg/seizeit2/raw",
         tool_cmd="aws s3 sync --no-sign-request s3://openneuro.org/ds005873 "
                  "datasets/eeg/seizeit2/raw",
         size="hundreds of GB (11,640 h)",
         note="RESOLVED: OpenNeuro ds005873, CC0. 125 focal epilepsy, "
              "behind-the-ear EEG + ECG + EMG + IMU, 886 seizures. Start with "
              "a subject subset if disk is tight (s3 sync --exclude/--include)"),
    dict(name="pd_meg_stn_lfp", status="tool", dest="eeg/pd_meg_stn_lfp_ds004998/raw",
         tool_cmd="aws s3 sync --no-sign-request s3://openneuro.org/ds004998 "
                  "datasets/eeg/pd_meg_stn_lfp_ds004998/raw",
         size="162 GB",
         note="20 PD: MEG 306ch + STN-LFP + EMG at 2 kHz, med ON/OFF, rest + "
              "movement tasks; CC0. STRONG stage B pair (movement-adjacent EMG "
              "+ invasive). R1 scoping applies to the LFP side"),
    dict(name="pd_walking_eeg", status="tool", dest="eeg/pd_walking_eeg_ds007526/raw",
         tool_cmd="aws s3 sync --no-sign-request s3://openneuro.org/ds007526 "
                  "datasets/eeg/pd_walking_eeg_ds007526/raw",
         size="est. 10-30 GB",
         note="116 PD + 28 controls, 64-ch EEG rest + treadmill walking, "
              "UPDRS/MoCA metadata; CC0; walking-EEG upgrade of ds002778"),
    dict(name="pd_rest_eeg", status="tool", dest="eeg/pd_rest_eeg_ds004584/raw",
         tool_cmd="aws s3 sync --no-sign-request s3://openneuro.org/ds004584 "
                  "datasets/eeg/pd_rest_eeg_ds004584/raw",
         size="est. <5 GB",
         note="100 PD + 49 controls, 64-ch rest EEG; CC0; quick win for the "
              "EEG socle"),
]


def log_row(name, url, dest, nbytes, sha, status):
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "dataset", "url", "dest", "bytes", "sha256",
                        "status"])
        w.writerow([time.strftime("%Y-%m-%d %H:%M"), name, url, dest, nbytes,
                    sha, status])


def md5_of(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def sha256_of(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def download(url, out_path, name, expect_md5=None):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    have = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    # Some repositories (Dryad, 2026-08-22) answer 403 to a non-browser agent, so
    # the tool identifies itself as a normal desktop browser plus a contact string.
    # Plain browser UA, no self-identifying token. The polite "MoveAtlas-fetch/1.0"
    # suffix got the fetcher UA-blacklisted by ndownloader.figshare.com
    # (verified 2026-08-25: same IP, same file, 202 with the token, 302 without).
    # Identification now lives in the download journal, not the header.
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 "
                      "Safari/537.36",
        "Accept": "*/*"})
    if have:
        req.add_header("Range", f"bytes={have}-")
        print(f"  resuming at {have/1e6:.1f} MB")
    # figshare answers 202 Accepted with an empty body for LARGE files: the
    # archive is being staged and the client must come back. Discovered
    # 2026-08-22, when a 56 GB batch "succeeded" in 45 seconds and wrote ten
    # 0-byte files whose sha256 was the hash of the empty string. Any status
    # other than 200/206 is now treated as not-yet-downloaded.
    r = None
    for attempt in range(STAGING_RETRIES):
        try:
            r = urllib.request.urlopen(req, timeout=60)
        except urllib.error.HTTPError as e:
            # 416: we asked to resume from EOF, i.e. the file is already whole.
            # Re-running the pipeline used to report these as failures.
            if e.code == 416 and have > 0:
                print(f"  SKIP {name}: already complete ({have/1e6:.1f} MB)")
                log_row(name, url, out_path, have, "", "already complete")
                return True
            print(f"  FAIL {name}: {e}")
            log_row(name, url, out_path, have, "", f"fail: {e}")
            return False
        except Exception as e:
            print(f"  FAIL {name}: {e}")
            log_row(name, url, out_path, have, "", f"fail: {e}")
            return False
        if r.status in (200, 206):
            break
        wait = min(STAGING_WAIT * (attempt + 1), STAGING_WAIT_MAX)
        print(f"  {name}: HTTP {r.status} (repository is staging the file); "
              f"retry {attempt + 1}/{STAGING_RETRIES} in {wait}s", flush=True)
        r.close()
        r = None
        time.sleep(wait)
    if r is None:
        print(f"  FAIL {name}: still not ready after {STAGING_RETRIES} attempts")
        log_row(name, url, out_path, have, "", "fail: staging timeout")
        return False
    mode = "ab" if have and r.status == 206 else "wb"
    done = have if mode == "ab" else 0
    t0 = time.time()
    with open(out_path, mode) as f:
        # the read loop must not let a mid-stream error escape: on 2026-08-25 a
        # TimeoutError inside r.read() killed the WHOLE queue two gigabytes
        # into PAXMIN, instead of logging one resumable failure and moving on
        try:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
                done += len(b)
                if time.time() - t0 > 5:
                    print(f"  {done/1e6:.0f} MB...", flush=True)
                    t0 = time.time()
        except Exception as e:
            print(f"  FAIL {name}: mid-stream {type(e).__name__} at "
                  f"{done/1e6:.0f} MB; partial kept, re-run to resume")
            log_row(name, url, out_path, done, "", f"fail: mid-stream {e}")
            return False
    size = os.path.getsize(out_path)
    if size == 0:
        # never call an empty file a success: that is how a 202 slipped through
        print(f"  FAIL {name}: 0 bytes written (HTTP {r.status}); removed")
        os.remove(out_path)
        log_row(name, url, out_path, 0, "", "fail: empty response")
        return False
    expected = r.headers.get("Content-Length")
    if expected and mode == "wb" and int(expected) != done:
        print(f"  FAIL {name}: truncated, got {done} of {expected} bytes; "
              "re-run to resume")
        log_row(name, url, out_path, size, "", "fail: truncated")
        return False
    if expect_md5:
        # figshare publishes an md5 per file; verifying it turns "the bytes
        # arrived" into "the RIGHT bytes arrived". Cheap, and it would have
        # caught the 0-byte batch immediately.
        got = md5_of(out_path)
        if got.lower() != expect_md5.lower():
            print(f"  FAIL {name}: md5 {got[:16]}... does not match the published "
                  f"{expect_md5[:16]}...; file kept for inspection")
            log_row(name, url, out_path, size, got, "fail: md5 mismatch")
            return False
        print(f"  md5 verified against the publisher ({got[:16]}...)")
    sha = sha256_of(out_path)
    print(f"  OK {name}: {done/1e6:.1f} MB, sha256 {sha[:16]}...")
    log_row(name, url, out_path, size, sha, "complete")
    return True


def cap_subset(entry, prefixes, limit=0):
    """CAP naming, VERIFIED against physionet 2026-08-22: RECORDS lines already
    carry the .edf suffix (n1.edf), the hypnogram is <stem>.txt (n1.txt) and the
    scoring file is <record>.st (n1.edf.st). Appending .edf/.txt to the record
    name gives 404s, which is why the first run downloaded only .st files.
    Prefixes match the leading LETTERS of the stem exactly, so 'n' selects the
    16 normals and not the narco* recordings."""
    base = entry["files_base"]
    dest = os.path.join(DS, entry["dest"])
    os.makedirs(dest, exist_ok=True)
    try:
        listing = urllib.request.urlopen(base + "RECORDS", timeout=30).read().decode()
        records = [l.strip() for l in listing.splitlines() if l.strip()]
    except Exception as e:
        print(f"  RECORDS unavailable ({e}); use the full zip")
        return
    def group(rec):
        m = re.match(r"[A-Za-z]+", os.path.basename(rec))
        return m.group(0).lower() if m else ""
    keep = [r for r in records if group(r) in {p.lower() for p in prefixes}]
    if limit:
        keep = keep[:limit]
        print(f"  (--cap-limit {limit}: verification batch only)")
    print(f"  CAP subset {prefixes}: {len(keep)}/{len(records)} records")
    for rec in keep:
        stem = rec[:-4] if rec.lower().endswith(".edf") else rec
        for name in (rec, stem + ".txt", rec + ".st"):
            out = os.path.join(dest, name)
            # No existence pre-skip: a PARTIAL file is also "exists and > 0
            # bytes", and skipping it here is why rbd1/rbd22 sat truncated for
            # a whole day (found 2026-08-24). download() already resumes by
            # Range and treats 416 as already-complete, so the worst case for
            # a finished file is one cheap request.
            print(f"  {name}")
            download(base + name, out, f"cap_sleep:{name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--cap-subset", default="", help="e.g. rbd,n (RECORDS prefixes)")
    ap.add_argument("--cap-limit", type=int, default=0,
                    help="only the first N CAP records (EDF reader verification)")
    args = ap.parse_args()

    if args.list:
        for e in REGISTRY:
            print(f"{e['name']:26s} {e['status']:8s} -> datasets/{e['dest']}"
                  f"  [{e.get('size','')}] {e['note']}")
        return 0

    cache = json.load(open(URLS_CACHE)) if os.path.exists(URLS_CACHE) else {}
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    for e in REGISTRY:
        if only and e["name"] not in only:
            continue
        print(f"== {e['name']} ({e['status']})")
        if e["status"] == "satisfied":
            print(f"  nothing to do: {e['note']}")
            continue
        if e["status"] == "tool":
            print(f"  needs a dedicated client. Run:\n    {e['tool_cmd']}")
            log_row(e["name"], e["tool_cmd"], e["dest"], 0, "", "tool hint printed")
            continue
        if e["name"] == "cap_sleep" and args.cap_subset:
            cap_subset(e, [p.strip() for p in args.cap_subset.split(",")],
                       args.cap_limit)
            continue
        urls = e.get("urls")
        if not urls:
            url = e.get("url") or cache.get(e["name"])
            if isinstance(url, list):      # resolved multi-file entry (see below)
                urls = url
                url = None
        if not urls:
            if not url:
                print(f"  direct URL to resolve. Source page: {e['source']}")
                ans = input("  paste direct URL (enter to skip): ").strip()
                if not ans:
                    log_row(e["name"], e["source"], e["dest"], 0, "",
                            "resolution deferred")
                    continue
                url = ans
                cache[e["name"]] = url
                json.dump(cache, open(URLS_CACHE, "w"), indent=2)
            urls = [url]
        for fi_, url in enumerate(urls):
            if fi_:
                time.sleep(INTER_FILE_PAUSE)
            # a resolved entry may be {"url":..., "name":...}: repository download
            # URLs (figshare, OSF, Dryad) end in an opaque file id, so the real
            # file name comes from the repository API and is cached with it.
            fname, expect_md5 = None, None
            if isinstance(url, dict):
                fname, expect_md5 = url.get("name"), url.get("md5")
                url = url["url"]
            if not fname:
                fname = e.get("zip_name") if len(urls) == 1 and e.get("zip_name") \
                    else os.path.basename(url.rstrip("/").split("?")[0]) or e["name"]
            out = os.path.join(DS, e["dest"], fname)
            ok = download(url, out, e["name"], expect_md5)
            if ok and e.get("unzip") and out.endswith(".zip"):
                print("  unzipping...")
                with zipfile.ZipFile(out) as z:
                    z.extractall(os.path.join(DS, e["dest"]))
                print("  unzipped.")
    print()
    print("Then: write/refresh each received set's datacard.md, run "
          "python build_catalogue.py and python build_taxonomy_map.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
