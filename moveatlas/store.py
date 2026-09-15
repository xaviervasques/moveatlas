# -*- coding: utf-8 -*-
"""The MoveAtlas record store: where harmonized canonical records live.

Three stores, one interface (path / glob_dir / list_dir / verify_manifest):

- LocalStore: the repository's datasets/ tree (the ingestion machine).
- RemoteStore: MoveAtlas's own Zenodo records, downloaded on demand into a
  local cache (~/.moveatlas/records or MOVEATLAS_CACHE) and sha256-verified
  against each record's files.csv manifest. Downloads resume from a .part
  file (Range requests), retry with backoff on transient errors, print a
  progress line for large files, and turn "no network" into OfflineError.
- HybridStore: local first, remote second, returned by open_store() when
  this machine has a repository AND the release ships a records table; a
  relpath absent locally is fetched from the dataset's record when one
  exists (docs/MoveAtlas_PLATFORM_DESIGN.md section 8: one click, one pip).

sha256 discipline: verify_manifest() checks record files against a
manifest CSV (path,sha256). Manifests are produced at release-assembly
time; local reads skip verification unless a manifest exists.

Environment: MOVEATLAS_REPO (repository root), MOVEATLAS_CACHE (download
cache), MOVEATLAS_QUIET=1 (no progress or retry lines on stderr).
"""
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile


class OfflineError(FileNotFoundError):
    """A record is not in the local cache and the network is unreachable
    (urllib URLError after the retries). Subclasses FileNotFoundError so
    callers that already handle "not here" keep working."""


def _repo_root():
    env = os.environ.get("MOVEATLAS_REPO")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    if os.path.isdir(os.path.join(root, "datasets")):
        return root
    raise FileNotFoundError(
        "MoveAtlas record store not found: set MOVEATLAS_REPO to the repository "
        "root (the directory containing datasets/), or wait for the "
        "public release which downloads records on demand")


def sha256_of(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _quiet():
    return os.environ.get("MOVEATLAS_QUIET", "").strip() == "1"


def _say(msg):
    if not _quiet():
        print(msg, file=sys.stderr, flush=True)


def _fmt_bytes(n):
    if n >= 1 << 30:
        return f"{n / (1 << 30):.2f} GB"
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MB"
    return f"{n / 1024:.0f} KB"


def _norm(relpath):
    return relpath.replace("\\", "/")


class LocalStore:
    """Serve record files from the local repository tree."""

    def __init__(self, root=None):
        self.root = root or _repo_root()

    def path(self, relpath):
        # a .pkl relpath resolves to its .npz sibling when the store has
        # been migrated (moveatlas-record/1); pre-migration stores still
        # answer the .pkl
        p = os.path.join(self.root, relpath)
        if relpath.endswith(".pkl") and os.path.exists(p[:-4] + ".npz"):
            return p[:-4] + ".npz"
        if not os.path.exists(p):
            raise FileNotFoundError(
                f"record not in the local store: {relpath} (root "
                f"{self.root}). If this machine never ingested the "
                "dataset, run its ingestion recipe first")
        return p

    def glob_dir(self, reldir, suffix=None):
        """Record files under reldir. Default: the .npz containers, falling
        back to legacy .pkl only when a directory holds no .npz at all."""
        d = os.path.join(self.root, reldir)
        if not os.path.isdir(d):
            raise FileNotFoundError(
                f"record directory not in the local store: {reldir} "
                f"(root {self.root})")
        names = [f for f in os.listdir(d) if not f.startswith("._")]
        for suf in ([suffix] if suffix else [".npz", ".pkl"]):
            hits = sorted(os.path.join(d, f) for f in names if f.endswith(suf))
            if hits:
                return hits
        return []

    def list_dir(self, reldir):
        """Immediate children of reldir as store-relative paths (forward
        slashes, sorted); sub-directories carry a trailing '/'. An absent
        directory answers [] (discovery, not access: nothing raises)."""
        reldir = _norm(reldir).rstrip("/")
        d = os.path.join(self.root, reldir)
        if not os.path.isdir(d):
            return []
        out = []
        for name in sorted(os.listdir(d)):
            if name.startswith("._"):
                continue
            rel = f"{reldir}/{name}"
            if os.path.isdir(os.path.join(d, name)):
                rel += "/"
            out.append(rel)
        return out

    def verify_manifest(self, manifest_csv):
        """Check every (path, sha256) row; return the list of failures."""
        bad = []
        with open(manifest_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                p = self.path(row["path"])
                if sha256_of(p) != row["sha256"].lower():
                    bad.append(row["path"])
        return bad


def _cache_root():
    env = os.environ.get("MOVEATLAS_CACHE")
    if env:
        return env
    return os.path.join(os.path.expanduser("~"), ".moveatlas", "records")


def _records_table():
    """dataset id -> {"record": zenodo record id, "doi": ...}, shipped with
    the package (moveatlas/data/zenodo_records.json, regenerated by
    build_records_table.py from the campaign journal at release time)."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "data", "zenodo_records.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


class _Progress:
    """One line per file with its size, then a line every 10 percent, for
    files over THRESHOLD bytes; silent otherwise and under
    MOVEATLAS_QUIET=1."""

    THRESHOLD = 50 << 20

    def __init__(self, what, total, done=0):
        self.what, self.total, self.done = what, total, done
        self.on = bool(total) and total > self.THRESHOLD and not _quiet()
        self.next = 10
        if self.on:
            tail = f", resuming at {_fmt_bytes(done)}" if done else ""
            _say(f"{what}: {_fmt_bytes(total)}{tail}")
            while self.next <= 100 and 100 * done // total >= self.next:
                self.next += 10

    def advance(self, n):
        self.done += n
        if not self.on:
            return
        pct = min(100, 100 * self.done // self.total)
        while self.next <= 100 and pct >= self.next:
            _say(f"  {self.what}: {self.next}% "
                 f"({_fmt_bytes(self.done)} / {_fmt_bytes(self.total)})")
            self.next += 10


class RemoteStore:
    """The Zenodo record store: downloads record files on demand into a
    local cache (~/.moveatlas/records or MOVEATLAS_CACHE) and verifies
    every byte against the record's own files.csv manifest (sha256).

    Two record layouts, both produced by upload_zenodo.py:

    - direct: one record file per store file, flat name = path with '/'
      replaced by '__'; manifest columns path,bytes,sha256,record_name.
    - bundled (>100-file datasets): ZIP parts; manifest columns
      path,bytes,sha256,zip_part[,zip_part_sha256]; members keep their
      true relpath. When zip_part_sha256 is present the part is verified
      before any extraction (once per process for cached parts).

    Transport: an interrupted download leaves <dest>.part and the next
    call resumes it with a Range header (a server that ignores the range
    restarts the file). Transient failures (URLError, HTTP 429 and 5xx)
    are retried RETRIES times with BACKOFF seconds between tries; 404 and
    other client errors raise at once. A URLError that survives the
    retries becomes OfflineError (a FileNotFoundError).

    An unpublished (still-draft) record answers 404 on the public API:
    the error says so honestly instead of guessing."""

    MANIFEST = "files.csv"
    RETRIES = 3
    BACKOFF = (5, 15, 45)
    CHUNK = 1 << 22

    def __init__(self, cache=None, api_base="https://zenodo.org/api",
                 table=None):
        self.cache = cache or _cache_root()
        self.api = api_base.rstrip("/")
        self.table = table if table is not None else _records_table()
        self._files = {}      # dataset id -> {key: file dict from the API}
        self._manifest = {}   # dataset id -> {path: manifest row}
        self._verified_parts = set()

    def __repr__(self):
        return f"<RemoteStore cache={self.cache!r} api={self.api!r}>"

    # -- resolution --------------------------------------------------
    @staticmethod
    def _dataset_of(relpath):
        parts = _norm(relpath).split("/")
        if len(parts) < 3 or parts[0] != "datasets":
            raise FileNotFoundError(
                f"cannot map '{relpath}' to a dataset id (expected "
                "datasets/<family>/<id>/...)")
        return parts[2]

    def has_record(self, relpath_or_id):
        """True when the release table lists a record for the dataset the
        relpath (or bare id) belongs to."""
        did = relpath_or_id
        if "/" in _norm(did):
            try:
                did = self._dataset_of(did)
            except FileNotFoundError:
                return False
        return did in self.table

    def _record_id(self, did):
        entry = self.table.get(did)
        if not entry:
            raise FileNotFoundError(
                f"'{did}' has no published MoveAtlas record in this "
                "release's table (moveatlas/data/zenodo_records.json); "
                "if the dataset is recipe/barrier tier, use its "
                "documented route instead")
        return entry["record"]

    # -- transport ---------------------------------------------------
    def _open(self, req, timeout, what):
        """urlopen with retries: RETRIES more tries after the first,
        BACKOFF[i] seconds apart, on URLError and on HTTP 429 / 5xx.
        404 and the other client errors raise immediately."""
        err = None
        for i in range(self.RETRIES + 1):
            try:
                return urllib.request.urlopen(req, timeout=timeout)
            except urllib.error.HTTPError as e:
                if e.code != 429 and not 500 <= e.code < 600:
                    raise
                err = e
            except urllib.error.URLError as e:
                err = e
            if i == self.RETRIES:
                break
            wait = self.BACKOFF[min(i, len(self.BACKOFF) - 1)]
            _say(f"  {what}: {err} - retry {i + 1}/{self.RETRIES} in "
                 f"{wait} s")
            time.sleep(wait)
        raise err

    def _offline(self, err, did, checked):
        return OfflineError(
            f"network unreachable while fetching a record file of '{did}' "
            f"({err.reason if hasattr(err, 'reason') else err}); the cache "
            f"{self.cache} has no verified copy (checked {checked}). This "
            "record needs network: connect, or point MOVEATLAS_REPO at a "
            "machine that ingested the dataset")

    def _api_files(self, did):
        if did not in self._files:
            rec = self._record_id(did)
            url = f"{self.api}/records/{rec}"
            try:
                with self._open(url, 60, f"record {rec}") as r:
                    payload = json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    raise FileNotFoundError(
                        f"record {rec} for '{did}' is not public (yet): "
                        "the deposit exists but has not been published, "
                        "or the id is wrong") from e
                raise
            except urllib.error.URLError as e:
                raise self._offline(e, did, os.path.join(self.cache, did)) \
                    from e
            self._files[did] = {f["key"]: f for f in payload["files"]}
        return self._files[did]

    def _download(self, url, tmp, offset, total, what):
        """Stream url into tmp, resuming at offset when the server honours
        the Range header (206); a 200 answer restarts the file."""
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        req = urllib.request.Request(url, headers=headers)
        try:
            r = self._open(req, 300, what)
        except urllib.error.HTTPError as e:
            if e.code == 416 and offset:
                # the .part is not a prefix of the file any more: restart
                os.remove(tmp)
                return self._download(url, tmp, 0, total, what)
            raise
        with r:
            status = getattr(r, "status", None) or 200
            if offset and status != 206:
                offset = 0
            if total is None:
                hdrs = getattr(r, "headers", None)
                length = hdrs.get("Content-Length") if hdrs else None
                if length and str(length).isdigit():
                    total = int(length) + offset
            prog = _Progress(what, total, offset)
            with open(tmp, "ab" if offset else "wb") as out:
                for block in iter(lambda: r.read(self.CHUNK), b""):
                    out.write(block)
                    prog.advance(len(block))

    def _fetch_record_file(self, did, key, dest, expected=None):
        files = self._api_files(did)
        if key not in files:
            raise FileNotFoundError(
                f"record for '{did}' has no file '{key}' "
                f"(files: {sorted(files)[:8]}...)")
        url = files[key]["links"]["self"]
        total = expected
        if total is None:
            size = files[key].get("size")
            total = int(size) if isinstance(size, (int, float)) else None
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".part"
        offset = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        if total is not None and offset >= total:
            offset = 0      # a .part at least as long as the file is junk
        try:
            self._download(url, tmp, offset, total, key)
        except urllib.error.HTTPError:
            raise
        except urllib.error.URLError as e:
            raise self._offline(e, did, dest) from e
        os.replace(tmp, dest)
        return dest

    def _rows(self, did):
        if did not in self._manifest:
            man = os.path.join(self.cache, did, "_" + self.MANIFEST)
            if not os.path.exists(man):
                self._fetch_record_file(did, self.MANIFEST, man)
            with open(man, newline="", encoding="utf-8") as f:
                self._manifest[did] = {row["path"]: row
                                       for row in csv.DictReader(f)}
        return self._manifest[did]

    @staticmethod
    def _bytes_of(row):
        b = (row.get("bytes") or "").strip()
        return int(b) if b.isdigit() else None

    # -- the LocalStore interface ------------------------------------
    def path(self, relpath):
        relpath = self.resolve(relpath)
        did = self._dataset_of(relpath)
        dest = os.path.join(self.cache, relpath)
        row = self._rows(did).get(relpath)
        if row is None:
            raise FileNotFoundError(
                f"'{relpath}' is not in the record manifest of '{did}'")
        if os.path.exists(dest) and sha256_of(dest) == row["sha256"].lower():
            return dest
        if row.get("zip_part"):
            self._extract_from_part(did, row, dest)
        else:
            key = row.get("record_name") or relpath.replace("/", "__")
            self._fetch_record_file(did, key, dest, self._bytes_of(row))
        got = sha256_of(dest)
        want = (row.get("sha256") or "").strip().lower()
        if not want:
            # An empty cell used to skip verification entirely, so a record
            # whose manifest lost a digest served arbitrary downloaded bytes
            # as if they had been checked. Refuse instead: the manifest is
            # the only thing standing between a reader and a tampered file.
            os.remove(dest)
            raise IOError(
                f"{relpath}: the record manifest carries no sha256 for this "
                "file, so the download cannot be verified. Refusing to serve "
                "unverified bytes; report this record as malformed.")
        if got != want:
            os.remove(dest)
            raise IOError(
                f"sha256 mismatch for {relpath}: manifest "
                f"{want[:12]}..., downloaded {got[:12]}...")
        return dest

    def _extract_from_part(self, did, row, dest):
        part = row["zip_part"]
        zpath = os.path.join(self.cache, did, "_parts", part)
        want = (row.get("zip_part_sha256") or "").strip().lower()
        if zpath not in self._verified_parts:
            fresh = False
            if not os.path.exists(zpath):
                self._fetch_record_file(did, part, zpath)
                fresh = True
            if want:
                got = sha256_of(zpath)
                if got != want and not fresh:
                    # a stale or truncated cached part: fetch it again
                    os.remove(zpath)
                    self._fetch_record_file(did, part, zpath)
                    got = sha256_of(zpath)
                if got != want:
                    os.remove(zpath)
                    raise IOError(
                        f"sha256 mismatch for zip part {part} of '{did}': "
                        f"manifest {want[:12]}..., downloaded {got[:12]}...")
            self._verified_parts.add(zpath)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with zipfile.ZipFile(zpath) as z, z.open(row["path"]) as src, \
                open(dest + ".part", "wb") as out:
            for block in iter(lambda: src.read(self.CHUNK), b""):
                out.write(block)
        os.replace(dest + ".part", dest)

    def glob_dir(self, reldir, suffix=None):
        reldir = _norm(reldir).rstrip("/") + "/"
        did = self._dataset_of(reldir)
        rows = self._rows(did)
        for suf in ([suffix] if suffix else [".npz", ".pkl"]):
            hits = sorted(p for p in rows
                          if p.startswith(reldir) and p.endswith(suf))
            if hits:
                return [self.path(p) for p in hits]
        raise FileNotFoundError(
            f"record manifest of '{did}' holds nothing under {reldir} "
            f"with suffix {suffix or '.npz/.pkl'}")

    def list_dir(self, reldir):
        """Immediate children of reldir according to the record manifest
        (nothing is downloaded): store-relative paths, sub-directories with
        a trailing '/'. [] when the manifest holds nothing there; a dataset
        without a published record raises FileNotFoundError."""
        reldir = _norm(reldir).rstrip("/") + "/"
        did = self._dataset_of(reldir)
        out = set()
        for p in self._rows(did):
            if not p.startswith(reldir):
                continue
            head, sep, _ = p[len(reldir):].partition("/")
            if head and not head.startswith("._"):
                out.add(reldir + head + ("/" if sep else ""))
        return sorted(out)

    def resolve(self, relpath):
        """A .pkl relpath maps to its .npz sibling when the record was
        published in the migrated format."""
        relpath = _norm(relpath)
        if relpath.endswith(".pkl"):
            did = self._dataset_of(relpath)
            if relpath[:-4] + ".npz" in self._rows(did):
                return relpath[:-4] + ".npz"
        return relpath

    def verify_manifest(self, manifest_csv):
        bad = []
        with open(manifest_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                p = self.path(row["path"])
                if sha256_of(p) != row["sha256"].lower():
                    bad.append(row["path"])
        return bad


class HybridStore(LocalStore):
    """Local first, remote second, same interface. A relpath the local
    tree lacks is served from the dataset's published record when the
    release table lists one; otherwise the local error (with its
    ingestion hint) stands. Being a LocalStore, `.root` and the local
    behaviour are unchanged for everything that exists on disk."""

    def __init__(self, root=None, remote=None, table=None):
        super().__init__(root)
        self.remote = remote if remote is not None else RemoteStore(table=table)

    def __repr__(self):
        return f"<HybridStore root={self.root!r} remote={self.remote!r}>"

    def path(self, relpath):
        try:
            return super().path(relpath)
        except FileNotFoundError:
            if not self.remote.has_record(relpath):
                raise
            return self.remote.path(relpath)

    def glob_dir(self, reldir, suffix=None):
        try:
            hits = super().glob_dir(reldir, suffix)
        except FileNotFoundError:
            if not self.remote.has_record(reldir):
                raise
            return self.remote.glob_dir(reldir, suffix)
        if hits or not self.remote.has_record(reldir):
            return hits
        try:
            return self.remote.glob_dir(reldir, suffix)
        except FileNotFoundError:
            return hits

    def list_dir(self, reldir):
        local = super().list_dir(reldir)
        if local or not self.remote.has_record(reldir):
            return local
        return self.remote.list_dir(reldir)


def open_store():
    """The hosted tier's store: the local repository when this machine has
    it (fronted by the published records for whatever it lacks, when the
    release ships a records table), else the public Zenodo record store
    (download-on-demand cache)."""
    try:
        local = LocalStore()
    except FileNotFoundError:
        return RemoteStore()
    table = _records_table()
    if table:
        return HybridStore(local.root, table=table)
    return local
