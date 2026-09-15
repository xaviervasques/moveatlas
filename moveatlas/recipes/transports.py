# -*- coding: utf-8 -*-
"""Origin-host transports for the recipe tier: download into the store's
raw/ directory, resumable, verified, journaled.

Every transport writes under `<root>/datasets/<family>/<id>/raw/` and
appends one line per completed file to `downloads.sha256` beside raw/
(the format every dataset directory of the repository already uses:
`<sha256>  <name>  <bytes>`). A file already present with the expected
size and checksum is not downloaded again, so a fetch can be re-run.

Nothing here needs more than the standard library, except the figshare
transport which shells out to curl: ndownloader.figshare.com answers
python's TLS stack with empty 202 bodies and curl's with the file
(established 2026-08-26, see tools/fetch/fetch_figshare_curl.py in the
public tree for the full account). curl ships with macOS and Windows 10+
and is a package away on Linux.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

UA = "moveatlas/recipes (+https://github.com/xaviervasques/moveatlas)"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


class FetchError(RuntimeError):
    """A transfer that could not be completed or verified."""


class ManualDownload(FetchError):
    """The host answers clients with a browser challenge: the file must be
    saved by hand. The message says which URL, into which path, and what
    size and checksum the file must have; fetch() then accepts the file
    it finds there (verified) and ingest() proceeds."""

    def __init__(self, url, dest, size=None, md5=None):
        self.url, self.dest, self.size, self.md5 = url, dest, size, md5
        want = []
        if size is not None:
            want.append(f"{size} bytes")
        if md5:
            want.append(f"md5 {md5}")
        super().__init__(
            f"{os.path.basename(dest)}: the host answers clients with a browser "
            f"challenge (empty HTTP 202). Download it in a browser:\n"
            f"  open   {url}\n"
            f"  save as {dest}\n"
            + (f"  expect {', '.join(want)}\n" if want else "")
            + "then run the same fetch again: a file already there with the "
            "expected size and checksum is accepted and journaled.")


def _say(msg):
    if os.environ.get("MOVEATLAS_QUIET", "").strip() != "1":
        print(msg, file=sys.stderr, flush=True)


def sha256_of(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def md5_of(path, chunk=1 << 22):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def raw_dir(root, path):
    """`<root>/<path>/raw`, created. `path` is the registry's dataset path
    (datasets/<family>/<id>)."""
    d = os.path.join(root, path.replace("/", os.sep), "raw")
    os.makedirs(d, exist_ok=True)
    return d


def journal(root, path, name, nbytes, sha):
    """Append one line to the dataset's downloads.sha256 unless the same
    (name, sha) is already there."""
    jp = os.path.join(root, path.replace("/", os.sep), "downloads.sha256")
    os.makedirs(os.path.dirname(jp), exist_ok=True)
    line = f"{sha}  {name}  {nbytes}\n"
    if os.path.exists(jp):
        with open(jp, encoding="utf-8") as f:
            if line in f.read():
                return
    with open(jp, "a", encoding="utf-8", newline="\n") as f:
        f.write(line)


def journaled(root, path):
    """{name: (sha256, bytes)} from the dataset's downloads.sha256."""
    jp = os.path.join(root, path.replace("/", os.sep), "downloads.sha256")
    out = {}
    if os.path.exists(jp):
        with open(jp, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3:
                    out[parts[1]] = (parts[0], int(parts[2]))
    return out


def _complete(dest, size=None, md5=None):
    if not os.path.exists(dest):
        return False
    if size is not None and os.path.getsize(dest) != size:
        return False
    if md5 is not None and md5_of(dest) != md5.lower():
        return False
    return True


def api_json(url, tries=5):
    """GET a JSON document, with retries on the transient codes."""
    r = urllib.request.Request(url, headers={"User-Agent": UA,
                                             "Accept": "application/json"})
    for a in range(tries):
        try:
            with urllib.request.urlopen(r, timeout=60) as x:
                return json.load(x)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and a < tries - 1:
                time.sleep(5 * (a + 1))
                continue
            raise FetchError(f"{url}: HTTP {e.code}") from e
        except urllib.error.URLError as e:
            if a < tries - 1:
                time.sleep(5 * (a + 1))
                continue
            raise FetchError(f"{url}: {e.reason}") from e


def download_url(url, dest, size=None, md5=None, tries=6):
    """Resumable urllib download to `dest` (via dest.part), verified
    against `size` and `md5` when given. Returns (bytes, sha256)."""
    if _complete(dest, size, md5):
        return os.path.getsize(dest), sha256_of(dest)
    part = dest + ".part"
    for a in range(tries):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        headers = {"User-Agent": UA}
        if have:
            headers["Range"] = f"bytes={have}-"
        r = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(r, timeout=120) as x:
                mode = "ab" if have and x.status == 206 else "wb"
                with open(part, mode) as f:
                    shutil.copyfileobj(x, f, 1 << 20)
            break
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            if a == tries - 1:
                raise FetchError(f"{url}: {e}") from e
            time.sleep(10 * (a + 1))
    if size is not None and os.path.getsize(part) != size:
        os.remove(part)
        raise FetchError(f"{os.path.basename(dest)}: got "
                         f"{os.path.getsize(part) if os.path.exists(part) else 0} "
                         f"bytes, expected {size}")
    if md5 is not None and md5_of(part) != md5.lower():
        os.remove(part)
        raise FetchError(f"{os.path.basename(dest)}: md5 mismatch after download")
    os.replace(part, dest)
    return os.path.getsize(dest), sha256_of(dest)


def curl_download(url, dest, size=None, md5=None, tries=6, pause=5):
    """The figshare path: curl does the transfer (see the module doc),
    resuming a .part; verified like download_url. Returns (bytes, sha256)."""
    if _complete(dest, size, md5):
        return os.path.getsize(dest), sha256_of(dest)
    curl = shutil.which("curl") or shutil.which("curl.exe")
    if not curl:
        raise FetchError("curl is not installed; figshare refuses python's "
                         "TLS stack, so this transport needs curl on PATH")
    part = dest + ".part"
    code = ""
    for a in range(tries):
        cmd = [curl, "-L", "--fail", "--silent", "--show-error", "-A", BROWSER_UA,
               "--retry", "3", "--retry-delay", "5", "-C", "-", "-o", part,
               "-w", "%{http_code}", url]
        run = subprocess.run(cmd, capture_output=True, text=True)
        rc, code = run.returncode, run.stdout.strip()[-3:]
        if rc == 33:            # server refused the resume: start over
            if os.path.exists(part):
                os.remove(part)
            run = subprocess.run([c for c in cmd if c not in ("-C", "-")],
                                 capture_output=True, text=True)
            rc, code = run.returncode, run.stdout.strip()[-3:]
        got = os.path.getsize(part) if os.path.exists(part) else 0
        if rc == 0 and got > 0 and (size is None or got == size):
            break
        if code == "202" and got == 0:
            # an empty 202 is the host's bot challenge (AWS WAF on
            # ndownloader.figshare.com since at least 2026-09-15): it is
            # answered by a browser, not by a client, and not by retrying
            if os.path.exists(part):
                os.remove(part)
            raise ManualDownload(url, dest, size, md5)
        _say(f"  curl exit {rc} (HTTP {code}), {got} bytes "
             f"(attempt {a + 1}/{tries}); waiting {pause * (a + 1)} s")
        if got == 0 and os.path.exists(part):
            os.remove(part)
        time.sleep(pause * (a + 1))
    else:
        raise FetchError(f"{os.path.basename(dest)}: curl could not complete "
                         f"the transfer in {tries} attempts (last HTTP {code})")
    if md5 is not None and md5_of(part) != md5.lower():
        os.remove(part)
        raise FetchError(f"{os.path.basename(dest)}: md5 mismatch after download")
    os.replace(part, dest)
    return os.path.getsize(dest), sha256_of(dest)


# -- hosts --------------------------------------------------------------------

def figshare_article(root, path, article_id, only=None, skip=None):
    """Fetch the files of a public figshare article into `<root>/<path>/raw`.
    `only` keeps the named files; `skip` drops the named ones (a way to
    leave a 5 GB video archive the atlas never ingests where it is).
    Returns the list of (name, bytes, sha256) fetched or already there."""
    art = api_json(f"https://api.figshare.com/v2/articles/{article_id}")
    files = art.get("files") or []
    if only:
        files = [f for f in files if f["name"] in set(only)]
    if skip:
        files = [f for f in files if f["name"] not in set(skip)]
    if not files:
        raise FetchError(f"figshare article {article_id}: no file selected")
    d = raw_dir(root, path)
    _say(f"figshare {article_id}: {art.get('title', '')[:70]}")
    _say(f"  licence on the article: {(art.get('license') or {}).get('name')}")
    out = []
    for f in files:
        dest = os.path.join(d, f["name"])
        _say(f"  {f['name']}: {f['size'] / 1e6:.1f} MB")
        n, sha = curl_download(f["download_url"], dest, size=f["size"],
                               md5=f.get("computed_md5"))
        journal(root, path, f["name"], n, sha)
        out.append((f["name"], n, sha))
    return out


def zenodo_record(root, path, record_id, only=None, skip=None):
    """Fetch the files of a public Zenodo record into `<root>/<path>/raw`,
    checksums verified against the record's own manifest."""
    rec = api_json(f"https://zenodo.org/api/records/{record_id}")
    files = rec.get("files") or []
    if only:
        files = [f for f in files if f["key"] in set(only)]
    if skip:
        files = [f for f in files if f["key"] not in set(skip)]
    if not files:
        raise FetchError(f"zenodo record {record_id}: no file selected")
    d = raw_dir(root, path)
    _say(f"zenodo {record_id}: {rec.get('metadata', {}).get('title', '')[:70]}")
    out = []
    for f in files:
        dest = os.path.join(d, f["key"])
        md5 = None
        if (f.get("checksum") or "").startswith("md5:"):
            md5 = f["checksum"][4:]
        url = (f.get("links") or {}).get("self") or \
            f"https://zenodo.org/api/records/{record_id}/files/{f['key']}/content"
        _say(f"  {f['key']}: {f['size'] / 1e6:.1f} MB")
        n, sha = download_url(url, dest, size=f["size"], md5=md5)
        journal(root, path, f["key"], n, sha)
        out.append((f["key"], n, sha))
    return out


def urls(root, path, named_urls):
    """Fetch plain URLs into `<root>/<path>/raw`: `named_urls` is
    {file name: url}. No checksum is known in advance; the journal records
    what arrived."""
    d = raw_dir(root, path)
    out = []
    for name, url in named_urls.items():
        dest = os.path.join(d, name)
        _say(f"  {name}: {url}")
        n, sha = download_url(url, dest)
        journal(root, path, name, n, sha)
        out.append((name, n, sha))
    return out
