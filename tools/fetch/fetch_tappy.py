#!/usr/bin/env python3
"""Resumable, throttle-tolerant fetch of the tappy PhysioNet zips."""
import os, time, urllib.request

BASE = "https://physionet.org/files/tappy/1.0.0/"
RAW = "datasets/auxdata/tappy_keystroke/raw"
FILES = ["Archived-Data.zip", "Archived-users.zip"]


def expected_len(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers.get("Content-Length", 0))


def fetch(name):
    url = BASE + name
    out = os.path.join(RAW, name)
    exp = expected_len(url)
    print(f"{name}: expected {exp} B", flush=True)
    for attempt in range(40):
        have = os.path.getsize(out) if os.path.exists(out) else 0
        if exp and have >= exp:
            print(f"  complete ({have})", flush=True)
            return True
        headers = {"User-Agent": "curl/8"}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as r:
                mode = "ab" if have and r.status == 206 else "wb"
                with open(out, mode) as f:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
        except Exception as e:
            wait = min(2 ** (attempt % 6), 30)
            print(f"  attempt {attempt}: {have}/{exp}  ({type(e).__name__}) backoff {wait}s", flush=True)
            time.sleep(wait)
    return (os.path.getsize(out) if os.path.exists(out) else 0) >= exp


ok = all(fetch(f) for f in FILES)
print("DONE ok=" + str(ok), flush=True)
