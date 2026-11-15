# -*- coding: utf-8 -*-
"""The 15 openly licensed motion-capture sets of the 2026-11-12 shortlist into datasets/pose/<id>/raw/.

Approved by the owner on 2026-11-12 (shortlist: MD_FM reports/open_mocap/README.md).
Exclusions decided with it: CMU's AVI archive (it shows the performers) is never
listed, only its C3D zips; nothing of ACCAD, TotalCapture, Transitions or any set
whose persons sit in the AMASS splits; not AddBiomechanics (it repackages several of
these sources); not the Warmerdam set (licence unclear). No source here needs an
account, a login or a form.

Usage (from the repo root, or with --moveatlas / MOVEATLAS_ROOT):
    python fetch_open_mocap.py resolve [--only a,b]   # host APIs -> fetch_manifest.json
    python fetch_open_mocap.py fetch   [--only a,b] [--workers 3]
    python fetch_open_mocap.py unpack  [--only a,b] [--dry-run]
    python fetch_open_mocap.py status

Per dataset, in datasets/pose/<id>/:
    fetch_manifest.json  one entry per file: URL, expected bytes, the host's checksum
                         (Zenodo md5, figshare md5, Mendeley sha256, OSF sha256; CMU
                         publishes none, so size from Content-Length only), plus the
                         files of the record left out and why
    fetch_log.json       licence as stated by the host, licence text URL, dates, and
                         per file the bytes, the checksum status, sha256 and attempts
    downloads.sha256     the house journal (sha256  relpath  bytes)
    raw/licence.txt      the licence text (CC legal code, or the CMU terms pages)
    raw/<files>          the data (raw/ is gitignored)

Transfer: curl.exe (resume with -C -, follow redirects), because figshare's
ndownloader refuses python/urllib (fetch_figshare_curl.py, 2026-08-26) and Zenodo
answers 403 to it. A file is written as <name>.part, resumed on the next attempt,
checked for size and checksum, then renamed; complete journaled files are skipped.
An empty-body 202 (figshare throttle) or any curl error is retried with a growing
wait. At most --workers transfers run at once, and one at a time per figshare.

unpack: Python's zipfile only, into raw/<zip stem>/, after a member-path traversal
check. An archive with any video member stays zipped and is reported; image members
are listed in the log and left inside the zip (only the other members are written
out, so no picture of a person can land unpacked). zipfile checks each member's CRC32
as it is read to its end, so an extraction is also the integrity check of a host
that publishes no checksum (CMU). tar.gz and 7z archives are listed (tarfile headers, the
system tar.exe for 7z), never extracted. Nothing downloaded is executed or imported.

Stdlib only.
"""
import argparse
import binascii
import datetime
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tarfile
import threading
import time
import zipfile

CC_BY_4 = ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/",
           "https://creativecommons.org/licenses/by/4.0/legalcode.txt")
CC0_1 = ("CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/",
         "https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt")
CMU_TERMS = ("CMU Graphics Lab terms (free for all uses; no direct resale, even in "
             "converted form)", "http://mocap.cs.cmu.edu/",
             ["http://mocap.cs.cmu.edu/", "http://mocap.cs.cmu.edu/faqs.php"])

VIDEO_EXT = {".avi", ".mp4", ".mov", ".mkv", ".webm", ".wmv", ".mpg", ".mpeg",
             ".m4v", ".flv", ".3gp", ".mts"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif", ".webp",
             ".heic"}

# select: exact file names (or "re:<pattern>") taken from the record; everything
# else of the record is written to the manifest's "excluded" list with the reason.
SOURCES = [
    dict(id="cmu_mocap", host="cmu", record="http://mocap.cs.cmu.edu/",
         title="CMU Graphics Lab Motion Capture Database, C3D",
         licence=CMU_TERMS,
         files=["allc3d_0.zip", "allc3d_1a.zip", "allc3d_1b.zip",
                "allc3d_234.zip", "allc3d_56789.zip"],
         excluded=[("allavi.zip", "video of the performers: never downloaded"),
                   ("allasfamc.zip", "skeleton fits of the same takes; the C3D "
                    "markers are the raw truth")]),
    dict(id="ceti_age_kinematics", host="figshare", record="26983645",
         title="CeTI-Age-Kinematics", licence=CC_BY_4,
         select=["ceti-age-kinematics.zip", "README_updated.md",
                 "dataset_description_updated.json"],
         reason="overview figure, not data"),
    dict(id="lex3d", host="osf", record="cv276",
         nodes=["p2cth", "9vgrx", "mqzyk", "3p2rm"],
         title="3D-LEX v1.0 (ASL and NGT), Vicon markers and FBX animation",
         licence=CC_BY_4,
         select=["ASL_Vicon_MarkerData.zip", "NGT_Vicon_MarkerData.zip",
                 "ASL_ANIM_FBX.zip", "NGT_ANIM_FBX.zip"],
         reason="GLB duplicates the FBX animation; handshape (15.1 GB) and "
                "face pose components are not in the approved selection",
         extra_excluded_nodes=["pxkv8", "928gk", "6rne3", "tsd9m"]),
    dict(id="horst_gait_fullbody", host="mendeley", record="svx74xcrjr", version=3,
         title="Horst et al. full-body gait (C3D)", licence=CC_BY_4,
         select=["Gait_rawdata_c3d.zip", "Gait_subject_info.csv"],
         reason="TSV exports of the same C3D trials"),
    dict(id="schreiber_moissenet_gait", host="figshare", record="7734767",
         title="Schreiber and Moissenet, gait at different walking speeds",
         licence=CC_BY_4, select=["re:.*"]),
    dict(id="lencioni_gait_stairs", host="figshare_collection", record="4494755",
         title="Lencioni et al., human kinematic, kinetic and EMG data during "
               "walking and stairs", licence=CC0_1, select=["re:.*"],
         licence_note="every figshare item states CC0; the data paper states CC BY "
                      "4.0: cite the paper either way"),
    dict(id="push_recovery_perturbations", host="zenodo", record="10512652",
         title="Full-body motion capture following external perturbations "
               "(push recovery)", licence=CC_BY_4, select=["re:.*"]),
    dict(id="moore_perturbed_gait", host="zenodo", record="13030",
         title="Moore et al., human gait and the effect of mechanical perturbations",
         licence=CC0_1, select=["re:.*"]),
    dict(id="shida_pd_gait", host="figshare", record="14896881",
         title="Shida et al., overground walking full-body kinematics in "
               "Parkinson's disease", licence=CC_BY_4,
         select=["C3Dfiles.zip", "PDGinfo.xlsx", "Supplementary_material.docx"],
         reason="time-normalised gait cycles derived from the same C3D"),
    dict(id="deepdance", host="zenodo", record="7950401",
         title="DeepDance: motion capture data of improvised dance",
         licence=CC_BY_4, select=["deep-dance-full.zip", "animate_tsv.m"],
         reason="music audio, not motion"),
    dict(id="umons_taichi", host="zenodo", record="2784581",
         title="UMONS-TAICHI, C3D", licence=CC_BY_4,
         select=["C3D.zip", "Labels.zip"],
         reason="TSV and segmented copies of the same takes; Kinect not wanted"),
    dict(id="notredame_noncyclic", host="figshare", record="28689221",
         title="Notre Dame whole-body optical marker and GRF data of non-cyclic "
               "activities", licence=CC_BY_4,
         select=["re:AB\\d\\d\\.zip", "Readme.pdf", "marker_set.xml"],
         reason="per-participant MAT, TAK and C3D copies, OpenSim geometry, "
                "MATLAB tools and figures: the approved selection is the 10 "
                "participant zips"),
    dict(id="style100", host="zenodo", record="8127870",
         title="100STYLE, BVH", licence=CC_BY_4, select=["100STYLE.zip"],
         reason="labelled copy (14.75 GB) not in the approved selection"),
    dict(id="sign_language_mocap_archive", host="zenodo", record="24149408",
         title="Sign Language Mocap Archive (Studio Galt), catalogue snapshot",
         licence=CC_BY_4, select=["re:.*"],
         licence_note="the GitHub repository states CC0-1.0; the Zenodo snapshot "
                      "states CC BY 4.0"),
    dict(id="vanderzee_walking", host="figshare_collection", record="5897423",
         title="Van der Zee et al., walking at 33 conditions, level 1 C3D",
         licence=CC0_1, articles=["19718500", "19714639"],
         select=["re:.*"],
         reason="levels 2 (CMO) and 3 (MAT) are derived from the level 1 C3D"),
]
SRC = {s["id"]: s for s in SOURCES}
FAMILY = "pose"
# figshare throttles bursts (one stream at a time); mocap.cs.cmu.edu serves about
# 0.1 MB/s per connection (measured 2026-11-12), so it keeps one stream while
# other hosts still have files waiting, and takes every slot once they are done.
HOST_LIMIT = {"figshare": 1, "cmu": 1}


def host_key(host):
    return "figshare" if host.startswith("figshare") else host


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def curl_text(url, binary=False):
    """GET a small resource (API JSON, licence page) through curl."""
    out = subprocess.run(["curl.exe", "-sSfL", "--retry", "4", "--retry-delay",
                          "10", "--connect-timeout", "40", url],
                         capture_output=True, check=True).stdout
    return out if binary else out.decode("utf-8", "replace")


def curl_json(url):
    for k in range(5):
        try:
            return json.loads(curl_text(url))
        except subprocess.CalledProcessError:
            time.sleep(20 * (k + 1))
    return json.loads(curl_text(url))


def head_size(url):
    hdr = subprocess.run(["curl.exe", "-sSIL", "--connect-timeout", "40", url],
                         capture_output=True, check=True).stdout.decode()
    sizes = re.findall(r"(?im)^content-length:\s*(\d+)", hdr)
    return int(sizes[-1]) if sizes else None


def wanted(name, select):
    for s in select:
        if s.startswith("re:"):
            if re.fullmatch(s[3:], name):
                return True
        elif s == name:
            return True
    return False


# ---------------------------------------------------------------- resolve
def resolve_zenodo(src):
    d = curl_json(f"https://zenodo.org/api/records/{src['record']}")
    files = [dict(name=f["key"], url=f["links"]["self"], bytes=f["size"],
                  checksum_type=f["checksum"].split(":")[0],
                  checksum=f["checksum"].split(":")[1]) for f in d["files"]]
    meta = dict(host_record=f"https://zenodo.org/records/{src['record']}",
                doi=d.get("doi"), host_title=d["metadata"]["title"],
                host_licence=(d["metadata"].get("license") or {}).get("id"),
                host_version=d["metadata"].get("version"),
                publication_date=d["metadata"].get("publication_date"))
    return meta, files


def figshare_files(aid):
    d = curl_json(f"https://api.figshare.com/v2/articles/{aid}")
    files = [dict(name=f["name"], url=f["download_url"], bytes=f["size"],
                  checksum_type="md5",
                  checksum=f.get("supplied_md5") or f.get("computed_md5") or "",
                  host_article=str(aid)) for f in d["files"]
             if not f.get("is_link_only")]
    return d, files


def resolve_figshare(src):
    d, files = figshare_files(src["record"])
    meta = dict(host_record=d.get("url_public_html") or d.get("figshare_url"),
                doi=d.get("doi"), host_title=d["title"],
                host_licence=d["license"]["name"], host_version=d.get("version"),
                publication_date=d.get("published_date"))
    return meta, files


def resolve_figshare_collection(src):
    cid = src["record"]
    c = curl_json(f"https://api.figshare.com/v2/collections/{cid}")
    arts = src.get("articles") or [str(a["id"]) for a in curl_json(
        f"https://api.figshare.com/v2/collections/{cid}/articles?page_size=500")]
    files, lic = [], set()
    for aid in arts:
        d, fs = figshare_files(aid)
        lic.add(d["license"]["name"])
        files += fs
        time.sleep(1)
    meta = dict(host_record=c.get("url_public_html") or c.get("figshare_url"),
                doi=c.get("doi"), host_title=c["title"],
                host_licence=sorted(lic), host_version=c.get("version"),
                publication_date=c.get("published_date"),
                host_articles=arts)
    return meta, files


def resolve_mendeley(src):
    slug, ver = src["record"], src["version"]
    base = f"https://data.mendeley.com/public-api/datasets/{slug}"
    files = []
    for f in curl_json(f"{base}/files?folder_id=root&version={ver}"):
        cd = f["content_details"]
        files.append(dict(name=f["filename"], url=cd["download_url"],
                          bytes=cd["size"], checksum_type="sha256",
                          checksum=(cd.get("sha256_hash") or "").lower()))
    dc = curl_json(f"https://api.datacite.org/dois/10.17632/{slug}.{ver}")
    at = dc["data"]["attributes"]
    meta = dict(host_record=f"https://data.mendeley.com/datasets/{slug}/{ver}",
                doi=f"10.17632/{slug}.{ver}", host_title=at["titles"][0]["title"],
                host_licence=[r.get("rights") for r in at.get("rightsList", [])
                              if r.get("rights")],
                host_version=ver, publication_date=at.get("publicationYear"))
    return meta, files


def osf_walk(url, prefix=""):
    while url:
        d = curl_json(url)
        for it in d["data"]:
            a = it["attributes"]
            if a["kind"] == "folder":
                yield from osf_walk(
                    it["relationships"]["files"]["links"]["related"]["href"],
                    prefix + a["name"] + "/")
            else:
                yield prefix + a["name"], a.get("size") or 0, (
                    a.get("extra", {}).get("hashes", {}).get("sha256") or ""
                ).lower(), it["links"]["download"]
        url = d.get("links", {}).get("next")


def resolve_osf(src):
    node = curl_json(f"https://api.osf.io/v2/nodes/{src['record']}/")
    lic_href = node["data"]["relationships"]["license"]["links"]["related"]["href"]
    lic = curl_json(lic_href)["data"]["attributes"]["name"]
    files = []
    for n in src["nodes"] + src.get("extra_excluded_nodes", []):
        for rel, size, sha, dl in osf_walk(
                f"https://api.osf.io/v2/nodes/{n}/files/osfstorage/"):
            files.append(dict(name=rel, url=dl, bytes=size, checksum_type="sha256",
                              checksum=sha, host_node=n))
    meta = dict(host_record=f"https://osf.io/{src['record']}/",
                doi=None, host_title=node["data"]["attributes"]["title"],
                host_licence=lic, host_version=None,
                publication_date=node["data"]["attributes"].get("date_created"))
    return meta, files


def resolve_cmu(src):
    files = []
    for name in src["files"]:
        url = f"http://mocap.cs.cmu.edu/{name}"
        files.append(dict(name=name, url=url, bytes=head_size(url),
                          checksum_type="none", checksum=""))
    meta = dict(host_record=src["record"], doi=None,
                host_title="CMU Graphics Lab Motion Capture Database",
                host_licence="free for all uses; may not be resold directly, even "
                             "in converted form (home page); may be copied, "
                             "modified, or redistributed without permission (FAQ)",
                host_version=None, publication_date=None)
    return meta, files


RESOLVERS = dict(zenodo=resolve_zenodo, figshare=resolve_figshare,
                 figshare_collection=resolve_figshare_collection,
                 mendeley=resolve_mendeley, osf=resolve_osf, cmu=resolve_cmu)


def ds_dir(root, sid):
    return os.path.join(root, "datasets", FAMILY, sid)


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cmd_resolve(root, ids):
    grand = 0
    for sid in ids:
        src = SRC[sid]
        meta, allf = RESOLVERS[src["host"]](src)
        if src["host"] == "cmu":
            keep, excl = allf, [dict(name=n, reason=r) for n, r in src["excluded"]]
        else:
            sel = src["select"]
            keep = [f for f in allf if wanted(f["name"], sel)
                    and f.get("host_node") not in src.get("extra_excluded_nodes", [])]
            excl = [dict(name=f["name"], bytes=f["bytes"],
                         reason=src.get("reason", "not selected"))
                    for f in allf if f not in keep]
        names = [f["name"] for f in keep]
        if len(names) != len(set(names)):
            sys.exit(f"{sid}: two selected files share a name: {names}")
        man = dict(dataset_id=sid, family=FAMILY, title=src["title"],
                   host=src["host"], resolved_at=now(),
                   licence=dict(name=src["licence"][0], url=src["licence"][1]),
                   licence_note=src.get("licence_note"), **meta,
                   n_files=len(keep), bytes=sum(f["bytes"] or 0 for f in keep),
                   files=keep, excluded=excl)
        d = ds_dir(root, sid)
        os.makedirs(d, exist_ok=True)
        write_json(os.path.join(d, "fetch_manifest.json"), man)
        grand += man["bytes"]
        print(f"{sid:30s} {len(keep):4d} files {man['bytes']/1e9:8.3f} GB  "
              f"excluded {len(excl)}  licence(host) {meta['host_licence']}")
    print(f"total {grand/1e9:.3f} GB")


# ---------------------------------------------------------------- licence
def strip_html(s):
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</tr>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def write_licence(root, sid, man):
    src = SRC[sid]
    raw = os.path.join(ds_dir(root, sid), "raw")
    os.makedirs(raw, exist_ok=True)
    path = os.path.join(raw, "licence.txt")
    name, url, text_src = src["licence"]
    if os.path.exists(path):
        return text_src
    head = [f"Dataset: {src['title']} (MoveAtlas id {sid})",
            f"Source record: {man.get('host_record')}",
            f"DOI: {man.get('doi')}",
            f"Licence as stated by the host at fetch time: {man.get('host_licence')}",
            f"Licence: {name} ({url})"]
    if src.get("licence_note"):
        head.append(f"Note: {src['licence_note']}")
    head.append(f"Retrieved: {now()}")
    if isinstance(text_src, list):
        body = []
        for u in text_src:
            body.append(f"\n===== {u} (page text) =====\n")
            body.append(strip_html(curl_text(u)))
        text = "\n".join(body)
        if "resell" not in text:
            raise RuntimeError("CMU terms page no longer carries the no-resale clause")
        head.append(f"Licence text source: {', '.join(text_src)}")
    else:
        text = curl_text(text_src)
        head.append(f"Licence text source: {text_src}")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(head) + "\n\n" + text.replace("\r\n", "\n"))
    return text_src


# ---------------------------------------------------------------- fetch
LOCK = threading.Lock()


def hashes_of(path):
    m, s = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            m.update(b)
            s.update(b)
    return m.hexdigest(), s.hexdigest()


def journal_read(d):
    p = os.path.join(d, "downloads.sha256")
    out = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                parts = ln.rstrip("\n").split("  ")
                if len(parts) >= 3:
                    out[parts[1]] = (parts[0], int(parts[2]))
    return out


def journal_add(d, sha, rel, size):
    with open(os.path.join(d, "downloads.sha256"), "a", encoding="utf-8",
              newline="\n") as f:
        f.write(f"{sha}  {rel}  {size}\n")


class Log:
    """fetch_log.json of one dataset, rewritten after every change."""

    def __init__(self, root, sid, man, text_src):
        self.path = os.path.join(ds_dir(root, sid), "fetch_log.json")
        old = read_json(self.path, {}) or {}
        self.d = dict(dataset_id=sid, family=FAMILY, title=man["title"],
                      source_record=man.get("host_record"), doi=man.get("doi"),
                      licence=man["licence"],
                      licence_as_stated_by_host=man.get("host_licence"),
                      licence_note=man.get("licence_note"),
                      licence_text_url=text_src,
                      licence_file="raw/licence.txt",
                      first_fetch=old.get("first_fetch") or now(),
                      last_run=now(), manifest_resolved_at=man["resolved_at"],
                      files=old.get("files", {}), excluded=man["excluded"],
                      unpack=old.get("unpack", {}))

    def file(self, name, **kw):
        with LOCK:
            self.d["files"].setdefault(name, {}).update(kw)
            self.d["last_run"] = now()
            write_json(self.path, self.d)

    def save(self):
        with LOCK:
            write_json(self.path, self.d)


def fetch_one(root, sid, f, log, max_attempts=10):
    d = ds_dir(root, sid)
    raw = os.path.join(d, "raw")
    dest = os.path.join(raw, *f["name"].split("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    part = dest + ".part"
    want = f["bytes"]
    jr = journal_read(d)
    if f["name"] in jr and os.path.exists(dest) and \
            os.path.getsize(dest) == jr[f["name"]][1]:
        log.file(f["name"], status="complete", note="journaled, skipped")
        return True
    if os.path.exists(dest) and not os.path.exists(part):
        os.replace(dest, part)          # unjournaled file: verify it again
    attempts = log.d["files"].get(f["name"], {}).get("attempts", 0)
    for k in range(1, max_attempts + 1):
        attempts += 1
        before = os.path.getsize(part) if os.path.exists(part) else 0
        log.file(f["name"], url=f["url"], expected_bytes=want,
                 checksum_type=f["checksum_type"], expected_checksum=f["checksum"],
                 status="downloading", attempts=attempts, started=now())
        if want and before == want:
            rc = 0
        else:
            rc = subprocess.call(
                ["curl.exe", "-sSL", "--fail", "-C", "-", "--retry", "3",
                 "--retry-delay", "20", "--connect-timeout", "40",
                 "--speed-limit", "2048", "--speed-time", "180",
                 "-o", part, f["url"]])
        after = os.path.getsize(part) if os.path.exists(part) else 0
        if rc == 33 or (want and after > want):
            # range refused, or more bytes than published: start again
            if os.path.exists(part):
                os.remove(part)
            msg = f"curl {rc}, restart from zero"
        elif rc == 0 and (not want or after == want):
            md5, sha = hashes_of(part)
            exp = (f["checksum"] or "").lower()
            got = {"md5": md5, "sha256": sha}.get(f["checksum_type"])
            if exp and got != exp:
                os.remove(part)
                log.file(f["name"], status="checksum mismatch", md5=md5,
                         sha256=sha, bytes=after)
                msg = f"{f['checksum_type']} mismatch ({got}), fresh download"
            else:
                os.replace(part, dest)
                journal_add(d, sha, f["name"], after)
                status = "verified" if exp else "size only (host gives no checksum)"
                log.file(f["name"], status="complete", checksum_status=status,
                         bytes=after, md5=md5, sha256=sha, completed=now())
                print(f"[{sid}] OK {f['name']} {after/1e6:.1f} MB, {status}",
                      flush=True)
                return True
        elif rc == 0 and after == before:
            if after == 0 and os.path.exists(part):
                os.remove(part)
            msg = "empty response (throttle or staging)"
        else:
            msg = f"curl exit {rc} at {after/1e6:.1f} of {(want or 0)/1e6:.1f} MB"
        wait = min(30 * 2 ** (k - 1), 900)
        print(f"[{sid}] {f['name']}: {msg}; attempt {k}/{max_attempts}, "
              f"next in {wait}s", flush=True)
        log.file(f["name"], status="retrying", last_error=msg, bytes=after)
        if k < max_attempts:
            time.sleep(wait)
    log.file(f["name"], status="failed")
    print(f"[{sid}] FAILED {f['name']}", flush=True)
    return False


def cmd_fetch(root, ids, workers):
    jobs, logs = [], {}
    for sid in ids:
        man = read_json(os.path.join(ds_dir(root, sid), "fetch_manifest.json"))
        if man is None:
            sys.exit(f"{sid}: no fetch_manifest.json; run resolve first")
        text_src = write_licence(root, sid, man)
        logs[sid] = Log(root, sid, man, text_src)
        logs[sid].save()
        for f in man["files"]:
            jobs.append((sid, SRC[sid]["host"], f))
    print(f"{len(jobs)} files, {sum(j[2]['bytes'] or 0 for j in jobs)/1e9:.3f} GB "
          f"in {len(ids)} datasets, {workers} at once", flush=True)
    pending, active, results = list(jobs), {}, []
    qlock = threading.Lock()

    def take():
        with qlock:
            hosts = {host_key(h) for _, h, _ in pending}
            for i, (sid, host, f) in enumerate(pending):
                h = host_key(host)
                limit = HOST_LIMIT.get(h, workers)
                if h == "cmu" and hosts == {"cmu"}:
                    limit = workers         # nothing else waits: every slot
                if active.get(h, 0) < limit:
                    active[h] = active.get(h, 0) + 1
                    return pending.pop(i)
            return None if not pending else "wait"

    def worker():
        while True:
            job = take()
            if job is None:
                return
            if job == "wait":
                time.sleep(5)
                continue
            sid, host, f = job
            try:
                ok = fetch_one(root, sid, f, logs[sid])
            except Exception as e:      # one file never kills the queue
                logs[sid].file(f["name"], status="failed", last_error=repr(e))
                ok = False
            results.append((sid, f["name"], ok))
            with qlock:
                active[host_key(host)] -= 1
            if host.startswith("figshare"):
                time.sleep(5)

    th = [threading.Thread(target=worker) for _ in range(workers)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    bad = [r for r in results if not r[2]]
    print(f"done: {len(results) - len(bad)} complete, {len(bad)} failed", flush=True)
    for r in bad:
        print("  failed:", r[0], r[1])
    return 1 if bad else 0


# ---------------------------------------------------------------- unpack
def member_kind(name):
    ext = os.path.splitext(name)[1].lower()
    return "video" if ext in VIDEO_EXT else "image" if ext in IMAGE_EXT else None


def mac_sidecar(name):
    """__MACOSX/ entries and ._ AppleDouble files that a Mac zip tool adds."""
    n = name.replace("\\", "/")
    return n.startswith("__MACOSX/") or n.split("/")[-1].startswith("._")


def same_as_loose(path, raw):
    """True when every member of the zip is already a loose file of raw/ with the
    same size and CRC32 (Lencioni's All_Subjects.zip repeats its 50 subject files)."""
    with zipfile.ZipFile(path) as z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        for i in infos:
            loose = os.path.join(raw, os.path.basename(i.filename))
            if not os.path.exists(loose) or os.path.getsize(loose) != i.file_size:
                return False
            crc = 0
            with open(loose, "rb") as f:
                for b in iter(lambda: f.read(1 << 22), b""):
                    crc = binascii.crc32(b, crc)
            if crc != i.CRC:
                return False
    return bool(infos)


def safe_member(name):
    n = name.replace("\\", "/")
    return not (n.startswith("/") or re.match(r"^[A-Za-z]:", n)
                or ".." in n.split("/"))


def list_archive(path):
    """Return (kind, [(name, size)]) without extracting anything."""
    low = path.lower()
    if low.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            return "zip", [(i.filename, i.file_size) for i in z.infolist()
                           if not i.is_dir()]
    if low.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path) as t:
            return "tar", [(m.name, m.size) for m in t.getmembers() if m.isfile()]
    if low.endswith(".7z"):
        out = subprocess.run([os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                           "System32", "tar.exe"), "-tvf", path],
                             capture_output=True, check=True).stdout.decode(
                                 "utf-8", "replace")
        mem = []
        for ln in out.splitlines():
            p = ln.split(None, 8)
            if len(p) == 9 and not p[0].startswith("d"):
                mem.append((p[8], int(p[4])))
        return "7z", mem
    return None, []


def cmd_unpack(root, ids, dry):
    for sid in ids:
        d = ds_dir(root, sid)
        man = read_json(os.path.join(d, "fetch_manifest.json"))
        log = read_json(os.path.join(d, "fetch_log.json"), {})
        log.setdefault("unpack", {})
        for f in man["files"]:
            path = os.path.join(d, "raw", *f["name"].split("/"))
            st = log.get("files", {}).get(f["name"], {}).get("status")
            if st != "complete" or not os.path.exists(path):
                continue
            kind, members = list_archive(path)
            if kind is None:
                continue
            vid = [m for m, _ in members if member_kind(m) == "video"]
            img = [m for m, _ in members if member_kind(m) == "image"]
            unsafe = [m for m, _ in members if not safe_member(m)]
            mac = [m for m, _ in members if mac_sidecar(m)]
            members = [(m, s) for m, s in members if not mac_sidecar(m)]
            vid = [m for m in vid if not mac_sidecar(m)]
            img = [m for m in img if not mac_sidecar(m)]
            rec = dict(archive=f["name"], kind=kind, n_members=len(members),
                       macos_sidecar_members=len(mac),
                       member_bytes=sum(s for _, s in members),
                       video_members=vid, image_members=img, unsafe_paths=unsafe,
                       checked=now())
            stem = re.sub(r"\.(zip|tar\.gz|tgz|tar|7z)$", "", os.path.basename(path),
                          flags=re.I)
            target = os.path.join(d, "raw", stem)
            if kind != "zip":
                rec["action"] = f"kept packed ({kind}: listed only, never extracted)"
            elif unsafe:
                rec["action"] = "kept zipped: member paths leave the folder"
            elif vid:
                rec["action"] = "kept zipped: holds video"
            elif same_as_loose(path, os.path.join(d, "raw")):
                rec["action"] = ("not extracted: every member is already a loose "
                                 "file of raw/ (same size and CRC32)")
            elif dry:
                rec["action"] = "dry run"
            else:
                done_mark = os.path.join(target, ".unpacked")
                if not os.path.exists(done_mark):
                    with zipfile.ZipFile(path) as z:
                        for i in z.infolist():
                            if member_kind(i.filename) == "image":
                                continue        # images stay inside the zip
                            if mac_sidecar(i.filename):
                                continue        # macOS resource forks, not data
                            out = os.path.normpath(os.path.join(target, i.filename))
                            if not out.startswith(os.path.normpath(target) + os.sep):
                                raise RuntimeError(f"{sid}: {i.filename} escapes")
                            if i.is_dir():
                                os.makedirs(out, exist_ok=True)
                                continue
                            os.makedirs(os.path.dirname(out), exist_ok=True)
                            with z.open(i) as src, open(out, "wb") as dst:
                                for b in iter(lambda: src.read(1 << 22), b""):
                                    dst.write(b)
                    with open(done_mark, "w", encoding="utf-8", newline="\n") as m:
                        m.write(now() + "\n")
                rec["action"] = f"extracted to raw/{stem}/ (zipfile)" + (
                    f"; its {len(img)} image members left inside the zip" if img
                    else "")
            log["unpack"][f["name"]] = rec
            print(f"[{sid}] {f['name']}: {len(members)} members, video {len(vid)}, "
                  f"image {len(img)}, unsafe {len(unsafe)} -> {rec['action']}",
                  flush=True)
        if not dry:
            write_json(os.path.join(d, "fetch_log.json"), log)


def cmd_status(root, ids):
    tot_w = tot_h = 0
    for sid in ids:
        d = ds_dir(root, sid)
        man = read_json(os.path.join(d, "fetch_manifest.json"))
        log = read_json(os.path.join(d, "fetch_log.json"), {}) or {}
        if man is None:
            print(f"{sid:30s} not resolved")
            continue
        have = 0
        for f in man["files"]:
            p = os.path.join(d, "raw", *f["name"].split("/"))
            have += os.path.getsize(p) if os.path.exists(p) else (
                os.path.getsize(p + ".part") if os.path.exists(p + ".part") else 0)
        st = [v.get("status") for v in log.get("files", {}).values()]
        tot_w += man["bytes"]
        tot_h += have
        print(f"{sid:30s} {have/1e9:7.3f}/{man['bytes']/1e9:7.3f} GB  "
              f"complete {st.count('complete')}/{man['n_files']}  "
              f"failed {st.count('failed')}")
    print(f"{'total':30s} {tot_h/1e9:7.3f}/{tot_w/1e9:7.3f} GB")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["resolve", "fetch", "unpack", "status"])
    ap.add_argument("--moveatlas", default=os.environ.get(
        "MOVEATLAS_ROOT", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    ids = [x.strip() for x in a.only.split(",") if x.strip()] or [s["id"] for s in SOURCES]
    for sid in ids:
        if sid not in SRC:
            sys.exit(f"unknown dataset id {sid}")
    if a.cmd == "resolve":
        cmd_resolve(a.moveatlas, ids)
    elif a.cmd == "fetch":
        return cmd_fetch(a.moveatlas, ids, max(1, min(a.workers, 3)))
    elif a.cmd == "unpack":
        cmd_unpack(a.moveatlas, ids, a.dry_run)
    else:
        cmd_status(a.moveatlas, ids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
