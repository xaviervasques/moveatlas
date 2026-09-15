# -*- coding: utf-8 -*-
"""Create DRAFT Zenodo deposits for the staged harmonized corpus.

Reads export/zenodo_staging/ (one dir per dataset: metadata.json +
files.csv, built by build_zenodo_staging.py) and, for every _plan.csv row
with target=zenodo, creates a DRAFT deposition via the Zenodo API, uploads
the record files, and sets the metadata. It NEVER publishes: drafts stay
private, each with a pre-reserved DOI, until the owner reviews and clicks
Publish on zenodo.org (the project's publication gate stays in the
owner's hands).

    python upload_zenodo.py --dry-run          # validate staging, no network
    python upload_zenodo.py --bundle           # zip the >100-file datasets
    ZENODO_TOKEN=... python upload_zenodo.py   # create drafts + upload
    python upload_zenodo.py --only gait120,hpo --sandbox

Facts this script encodes (verified 2026-09-02):
- a Zenodo record caps at 50 GB and 100 files; the 6 staged sets over
  100 files (gaitrec, gait120, pd_walking_eeg_ds007526, pd_rest_eeg_
  ds004584, cervical_motion_multiplanar, multimodal_fog) are bundled
  into ZIP parts by --bundle first (files.csv rides inside each zip);
- staging files.csv paths are Windows-style and their sha256 column is
  empty: paths are normalized here and checksums computed at upload;
  the normalized, checksummed files.csv is uploaded with each record;
- individual (non-bundled) uploads flatten paths with '__' since Zenodo
  records have no directories; files.csv maps flat names back to paths.

Token: create at zenodo.org/account/settings/applications/tokens/new
with scopes deposit:write + deposit:actions, then export ZENODO_TOKEN.
The token is read from the environment only, never logged. State journal
in export/zenodo_staging/_uploaded.json makes reruns resume: finished
files are skipped by md5, existing drafts are reused, a lost connection
costs one file, not the campaign. Stdlib only.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = os.environ.get("MOVEATLAS_REPO") or os.environ.get("KINEFM_REPO", ".")
STAGING = os.path.join(REPO, "export", "zenodo_staging")
STATE = os.path.join(STAGING, "_uploaded.json")
ZIP_PART_CAP = 45e9          # stay under the 50 GB record cap with margin
CHUNK = 1 << 22


def _api(sandbox):
    return ("https://sandbox.zenodo.org/api" if sandbox
            else "https://zenodo.org/api")


def _req(url, token, method="GET", data=None, ctype="application/json",
         clen=None):
    # data goes through the Request CONSTRUCTOR: assigning req.data later
    # (or passing data to urlopen) triggers the Request.data setter, which
    # silently REMOVES any Content-Length header (CPython issue 16464) -
    # urllib then falls back to chunked transfer on file objects, and the
    # post-Invenio bucket API reads a chunked body as EMPTY ("Empty files
    # are not accepted"). Constructor first, headers after.
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    if data is not None and ctype:
        req.add_header("Content-Type", ctype)
    if clen is not None:
        req.add_header("Content-Length", str(clen))
    for attempt in range(5):
        if hasattr(data, "seek"):
            data.seek(0)  # a retry must not resend a consumed stream
        try:
            with urllib.request.urlopen(req) as r:
                body = r.read()
                return json.loads(body) if body else {}
        except urllib.error.URLError as e:
            # one clause for both: HTTPError (has .code) and bare
            # URLError (DNS blip / socket drop, no .code). Retryable:
            # 429/5xx and every no-code network error. The 2026-09-04
            # afternoon DNS outage outlived the old 5x30s ladder, so
            # the no-code ladder is longer and capped per attempt.
            code = getattr(e, "code", None)
            retryable = code in (429, 500, 502, 503, 504) or code is None
            if retryable and attempt < 4:
                time.sleep(min(300, 60 * (attempt + 1)) if code is None
                           else 30 * (attempt + 1))
                continue
            if code is not None:
                sys.stderr.write(f"HTTP {code} on {url}: "
                                 f"{e.read().decode(errors='replace')[:300]}\n")
            else:
                sys.stderr.write(f"network error on {url}: {e.reason}\n")
            raise


def _hashes(path):
    md5, sha = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            md5.update(block)
            sha.update(block)
    return md5.hexdigest(), sha.hexdigest()


def read_staging(only=None):
    """Yield (id, target, metadata, [(repo_relpath, abspath, bytes)])."""
    with open(os.path.join(STAGING, "_plan.csv"), newline="",
              encoding="utf-8") as f:
        plan = list(csv.DictReader(f))
    for row in plan:
        did = row["id"]
        if row["target"] != "zenodo" or (only and did not in only):
            continue
        d = os.path.join(STAGING, did)
        with open(os.path.join(d, "metadata.json"), encoding="utf-8") as f:
            meta = json.load(f)
        files = []
        with open(os.path.join(d, "files.csv"), newline="",
                  encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rel = r["path"].replace("\\", "/")
                files.append((rel, os.path.join(REPO, rel),
                              int(r["bytes"])))
        yield did, meta, files


def dry_run(only):
    bad = ok = 0
    for did, meta, files in read_staging(only):
        missing = [rel for rel, p, _ in files if not os.path.exists(p)]
        drift = [rel for rel, p, b in files
                 if os.path.exists(p) and os.path.getsize(p) != b]
        n, size = len(files), sum(b for _, _, b in files)
        note = "BUNDLE (>100 files)" if n > 100 else "direct"
        line = (f"  {did:30s} {n:5d} files {size/1e9:8.2f} GB  {note}")
        if n == 0:
            bad += 1
            print(line + "  PROBLEM: no staged files (nothing under "
                         "processed/ at staging time; ingest or drop "
                         "from the plan)")
            continue
        if missing or drift:
            bad += 1
            print(line + f"  PROBLEM: {len(missing)} missing, "
                         f"{len(drift)} size-drifted")
            for rel in (missing + drift)[:3]:
                print(f"      {rel}")
        else:
            ok += 1
            print(line)
    print(f"{ok} staged deposits clean, {bad} with problems")
    return 1 if bad else 0


def bundle_is_current(did):
    """True when the zip parts already hold exactly the staged file list.

    Compared by CONTENT, not by timestamp: re-running the staging rewrites
    files.csv even when nothing about the record changed, and an mtime test
    then demands a rebuild of tens of gigabytes of zips whose contents are
    identical. The bundler adds a zip_part column, so only path and sha256
    are compared."""
    outdir = os.path.join(STAGING, did, "bundle")
    if not os.path.exists(os.path.join(outdir, "BUNDLED.ok")):
        return False
    staged = os.path.join(STAGING, did, "files.csv")
    if not os.path.exists(staged):
        return False

    def key(rows):
        return {(r["path"].replace("\\", "/"), (r.get("sha256") or "").lower())
                for r in rows}

    with open(staged, newline="", encoding="utf-8") as f:
        want = key(csv.DictReader(f))
    zips = sorted(n for n in os.listdir(outdir) if n.endswith(".zip"))
    if not zips:
        return False
    try:
        with zipfile.ZipFile(os.path.join(outdir, zips[0])) as z:
            have = key(csv.DictReader(
                io.StringIO(z.read("files.csv").decode("utf-8"))))
    except (KeyError, zipfile.BadZipFile, OSError):
        return False
    return have == want


def bundle(only):
    """Zip every >100-file dataset into ZIP parts under its staging dir."""
    for did, meta, files in read_staging(only):
        if len(files) <= 100:
            continue
        outdir = os.path.join(STAGING, did, "bundle")
        os.makedirs(outdir, exist_ok=True)
        done = os.path.join(outdir, "BUNDLED.ok")
        files_csv = os.path.join(STAGING, did, "files.csv")
        if os.path.exists(done):
            if bundle_is_current(did):
                print(f"  {did}: bundle already holds the staged files, "
                      "skipping")
                continue
            print(f"  {did}: staged file list changed, rebuilding the parts")
        # always start from an empty directory: a crash mid-bundle leaves
        # orphan parts that the next upload would otherwise ship
        if os.path.isdir(outdir):
            for n in os.listdir(outdir):
                os.remove(os.path.join(outdir, n))
        rows, part, part_bytes, zf = [], 1, 0, None

        def _open_part(n):
            p = os.path.join(outdir, f"{did}_canonical_part{n}.zip")
            return zipfile.ZipFile(p, "w", zipfile.ZIP_STORED,
                                   allowZip64=True), p
        zf, zpath = _open_part(part)
        print(f"  {did}: bundling {len(files)} files")
        for rel, p, b in files:
            if part_bytes + b > ZIP_PART_CAP and part_bytes > 0:
                zf.close()
                part += 1
                part_bytes = 0
                zf, zpath = _open_part(part)
            zf.write(p, rel)
            part_bytes += b
            _, sha = _hashes(p)
            rows.append([rel, b, sha, os.path.basename(zpath)])
        man = os.path.join(outdir, "files.csv")
        with open(man, "w", newline="\n", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["path", "bytes", "sha256", "zip_part"])
            w.writerows(rows)
        zf.write(man, "files.csv")
        zf.close()
        with open(done, "w") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S\n"))
        # the freshness check compares this mtime with files.csv; set it
        # explicitly (a recreated file kept an old mtime on the corpus
        # volume on 2026-09-08 and three fresh bundles were skipped)
        now = time.time()
        os.utime(done, (now, now))
        print(f"    -> {part} part(s) in {outdir}")


def _state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(st):
    with open(STATE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(st, f, indent=1, sort_keys=True)


def upload(only, sandbox):
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        sys.exit("set ZENODO_TOKEN (zenodo.org > Applications > tokens, "
                 "scopes deposit:write + deposit:actions); this script "
                 "creates PRIVATE DRAFTS only and never publishes")
    api = _api(sandbox)
    st = _state()
    for did, meta, files in read_staging(only):
        if not files:
            print(f"{did}: SKIP, zero staged files (ingest or drop "
                  "from the plan)")
            continue
        key = ("sandbox:" if sandbox else "") + did
        entry = st.get(key, {})
        if not entry.get("deposition"):
            dep = _req(api + "/deposit/depositions", token, "POST", b"{}")
            entry = {"deposition": dep["id"],
                     "doi": dep.get("metadata", {})
                               .get("prereserve_doi", {}).get("doi", ""),
                     "bucket": dep["links"]["bucket"], "files": {}}
            st[key] = entry
            _save_state(st)
            print(f"{did}: draft {dep['id']} created, "
                  f"DOI reserved {entry['doi']}")
        _req(f"{api}/deposit/depositions/{entry['deposition']}", token,
             "PUT", json.dumps(meta).encode())
        bundled = os.path.join(STAGING, did, "bundle")
        files_csv = os.path.join(STAGING, did, "files.csv")
        if len(files) > 100:
            ok = os.path.join(bundled, "BUNDLED.ok")
            if not os.path.exists(ok):
                print(f"{did}: SKIP, needs --bundle first (>100 files)")
                continue
            if not bundle_is_current(did):
                print(f"{did}: SKIP, the zip parts do not hold the staged "
                      "file list - rerun --bundle")
                continue
            todo = [(n, os.path.join(bundled, n)) for n in
                    sorted(f for f in os.listdir(bundled)
                           if not f.startswith("._"))  # volume ghosts
                    if n.endswith(".zip") or n == "files.csv"]
        else:
            man = os.path.join(STAGING, did, "files_sha256.csv")
            # rebuilt whenever the staging is newer than the cached
            # manifest (a re-stage changes the file list, e.g. the pickle
            # -> npz migration)
            if not os.path.exists(man) or \
                    os.path.getmtime(man) < os.path.getmtime(files_csv):
                with open(man, "w", newline="\n", encoding="utf-8") as f:
                    w = csv.writer(f, lineterminator="\n")
                    w.writerow(["path", "bytes", "sha256", "record_name"])
                    for rel, p, b in files:
                        _, sha = _hashes(p)
                        w.writerow([rel, b, sha, rel.replace("/", "__")])
            todo = [("files.csv", man)]
            todo += [(rel.replace("/", "__"), p) for rel, p, _ in files]
        # An existing draft may hold files the staging no longer lists
        # (the pickle -> npz migration replaced every record file): remove
        # them from the draft so a published record carries only the
        # current files.csv. Drafts only - a published record's files are
        # immutable and this code never touches one.
        wanted = {name for name, _ in todo}
        # Read the file list from the DEPOSITION, not from the /files
        # collection: the collection endpoint times out on large drafts and
        # its ids went stale after the Invenio migration, which made every
        # DELETE answer 404 while the loop reported success (found
        # 2026-09-09). Delete through each file's own links.self.
        dep = _req(f"{api}/deposit/depositions/{entry['deposition']}", token)
        stale = [f for f in dep.get("files", [])
                 if f.get("filename") not in wanted]
        for rf in stale:
            url = (rf.get("links", {}) or {}).get("self")
            if not url:
                sys.exit(f"  {did}: cannot delete {rf.get('filename')}: the "
                         "API returned no self link; refusing to publish a "
                         "record with an unexpected file")
            print(f"  {did}: removing stale draft file {rf.get('filename')}")
            _req(url, token, "DELETE")
            entry["files"].pop(rf.get("filename"), None)
            _save_state(st)
        if stale:
            # prove the deletions landed: a silently failed cleanup would
            # publish the very files this block exists to remove
            after = _req(f"{api}/deposit/depositions/{entry['deposition']}",
                         token)
            left = [f["filename"] for f in after.get("files", [])
                    if f.get("filename") not in wanted]
            if left:
                sys.exit(f"  {did}: {len(left)} stale file(s) survived the "
                         f"cleanup, e.g. {left[0]}. Nothing was published; "
                         "re-run after checking the draft by hand.")
        for name, path in todo:
            md5, _ = _hashes(path)
            if entry["files"].get(name) == md5:
                continue
            size = os.path.getsize(path)
            print(f"  {did}: uploading {name} ({size/1e6:.1f} MB)")
            with open(path, "rb") as f:
                # ctype=None let urllib default to x-www-form-urlencoded,
                # which Zenodo now 415s: the bucket API requires octet-stream
                # percent-encode: source filenames may carry spaces
                # (lance_adams supplementary PDFs) and urllib refuses
                # raw spaces in a URL
                r = _req(entry["bucket"] + "/" + urllib.parse.quote(name),
                         token, "PUT",
                         f, ctype="application/octet-stream", clen=size)
            got = r.get("checksum", "").split(":", 1)[-1]
            if got != md5:
                sys.exit(f"  {did}/{name}: checksum mismatch after "
                         f"upload ({got} != {md5}); rerun to retry")
            entry["files"][name] = md5
            _save_state(st)
        print(f"{did}: draft complete "
              f"({len(entry['files'])} files, DOI {entry['doi']})")
    print("ALL DRAFTS READY. Review and publish on zenodo.org "
          "(uploads page); nothing is public yet.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--only", help="comma-separated dataset ids")
    ap.add_argument("--sandbox", action="store_true",
                    help="use sandbox.zenodo.org (separate token)")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    if a.dry_run:
        sys.exit(dry_run(only))
    if a.bundle:
        return bundle(only)
    upload(only, a.sandbox)


if __name__ == "__main__":
    main()
