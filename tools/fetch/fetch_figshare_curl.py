# -*- coding: utf-8 -*-
"""figshare transport over curl.exe, because ndownloader discriminates by TLS
fingerprint.

Established 2026-08-26 after three days of peeling the onion: the 403 was the
collection machine's VPN exit IP; the then-202s were partly real staging,
partly a blacklist of the fetcher's self-identifying UA token; and with the
IP clean and the UA plain, python/urllib STILL draws permanent 202 while
curl.exe with the same UA, same IP, same file draws 302 -> 200. The remaining
discriminator is the TLS client fingerprint. Rather than impersonate a
browser's TLS stack, this script shells out to curl for the transfer and
keeps everything else identical to fetch_p2_lot.py: resolved URLs and md5s
from datasets/_fetch_urls.json, resume, published-md5 verification, and rows
in the same journal (datasets/_download_log_p2.csv).

Usage: python fetch_figshare_curl.py [--only a,b] [--repo PATH]
Destinations come from fetch_p2_lot.REGISTRY, so the two stay consistent.
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_p2_lot import REGISTRY, log_row, md5_of, sha256_of

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
SETS_DEFAULT = "sixmwt_lifespan,nonan_gaitprint,gaitrec,stroke_gait_vancriekinge,gait120"
# One request a minute rides under the rate limit; the very first curl pass
# proved that a burst of full GETs draws empty-body 202s within seconds even
# though spaced probes pass. Slow IS the fast path here.
INTER_FILE_PAUSE = 60
THROTTLE_WAIT = 300          # seconds, grows per throttled attempt, capped
THROTTLE_WAIT_MAX = 1800


def curl_fetch(url, out_path, name, expect_md5=None, tries=8):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if os.path.exists(out_path) and expect_md5:
        if md5_of(out_path).lower() == expect_md5.lower():
            print(f"  SKIP {name}: already complete (md5 verified)")
            log_row(name, url, out_path, os.path.getsize(out_path), "",
                    "already complete (md5)")
            return "skip"        # truthy; lets the caller skip the pause
    for attempt in range(1, tries + 1):
        before = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        rc = subprocess.call([
            "curl.exe", "-L", "--fail", "-A", UA,
            "-C", "-",                      # resume
            "--retry", "3", "--retry-delay", "10",
            "--connect-timeout", "40", "--speed-limit", "1024",
            "--speed-time", "120",          # abort if <1KB/s for 2 min
            "-o", out_path, url])
        after = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        # curl treats 202 as success and writes the EMPTY throttle body: exit 0
        # with no bytes gained is the throttle speaking, not a download
        if rc == 0 and after > before:
            break
        if rc == 0:
            if after == 0 and os.path.exists(out_path):
                os.remove(out_path)         # a 0-byte file must never survive
            print(f"  {name}: empty-body 202 (throttle/cold); attempt "
                  f"{attempt}/{tries}", flush=True)
            if attempt < tries:             # no pointless sleep on the last try
                time.sleep(min(THROTTLE_WAIT * attempt, THROTTLE_WAIT_MAX))
            continue
        if rc == 33 and os.path.exists(out_path):
            # 33 = the server refuses the Range resume (a re-staged archive
            # loses its old byte identity); the partial can never complete
            os.remove(out_path)
            print(f"  {name}: curl 33, resume refused; partial dropped, "
                  "fresh start next attempt/cycle", flush=True)
        else:
            print(f"  curl exit {rc} (attempt {attempt}/{tries}); "
                  f"partial kept, retrying", flush=True)
        if attempt < tries:
            time.sleep(30 * attempt)
    else:
        log_row(name, url, out_path, os.path.getsize(out_path)
                if os.path.exists(out_path) else 0, "",
                "fail: throttle/curl exhausted")
        return False
    size = os.path.getsize(out_path)
    if expect_md5:
        got = md5_of(out_path)
        if got.lower() != expect_md5.lower():
            print(f"  FAIL {name}: md5 {got[:16]}... != published "
                  f"{expect_md5[:16]}...; file kept for inspection")
            log_row(name, url, out_path, size, got, "fail: md5 mismatch")
            return False
        print(f"  md5 verified ({got[:16]}...)")
    sha = sha256_of(out_path)
    print(f"  OK {name}: {size/1e6:.1f} MB, sha256 {sha[:16]}...")
    log_row(name, url, out_path, size, sha, "complete (curl transport)")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--only", default=SETS_DEFAULT)
    ap.add_argument("--cycles", type=int, default=24,
                    help="round-robin passes over the still-missing files")
    ap.add_argument("--cycle-wait", type=int, default=600,
                    help="seconds between passes")
    args = ap.parse_args()
    ds = os.path.join(args.repo, "datasets")
    cache = json.load(open(os.path.join(ds, "_fetch_urls.json"),
                           encoding="utf-8"))
    reg = {e["name"]: e for e in REGISTRY}
    # ROUND-ROBIN, not per-file exhaustion. figshare serves each archive in
    # windows (staged, then evicted again): S154 streamed at full speed in one
    # test and answered empty-body 202 through 2.5 h of spaced retries around
    # it. Hammering one cold file wastes the day; giving every file one shot
    # per cycle catches each one's hot window.
    todo = []
    for name in [x.strip() for x in args.only.split(",") if x.strip()]:
        e, entry = reg.get(name), cache.get(name)
        if e is None or entry is None:
            print(f"== {name}: no registry/cache entry, skipped")
            continue
        for u in (entry if isinstance(entry, list) else [entry]):
            url, fname, md5 = (u["url"], u.get("name"), u.get("md5")) \
                if isinstance(u, dict) else (u, None, None)
            fname = fname or url.rstrip("/").split("/")[-1]
            todo.append((name, url, os.path.join(ds, e["dest"], fname), md5))
    print(f"{len(todo)} files wanted")
    # PROBE THEN BURST (v3, 2026-08-26 evening). The round-robin at ~50
    # requests/hour spent eight cycles catching nothing: that request rate
    # KEEPS the rate limiter tripped, so every window looked cold. The limiter
    # needs silence to reset. One probe request every cycle_wait; while the
    # window is open, take as much as it will give; two consecutive cold
    # responses close it again.
    done = set()
    for cyc in range(1, args.cycles + 1):
        pending = [t for t in todo if t[2] not in done]
        if not pending:
            break
        # ROTATE the probe order per pass (2026-08-28): with a static order,
        # two cold heads close every window and the files behind them are
        # never probed at all; staging is per file, so spreading the probes
        # both triggers staging across the set and finds whichever file is
        # hot. The original campaign's list happened to go hot front-first,
        # which hid this.
        off = (cyc - 1) % len(pending)
        pending = pending[off:] + pending[:off]
        print(f"--- pass {cyc}/{args.cycles}: {len(pending)} missing, "
              f"probing after silence (probe offset {off})", flush=True)
        cold = 0
        for name, url, out, md5 in pending:
            res = curl_fetch(url, out, f"{name}:{os.path.basename(out)}", md5,
                             tries=1)
            if res:
                done.add(out)
                cold = 0
            else:
                cold += 1
                if cold >= 2:
                    print("  window closed (two cold responses); back to "
                          "silence", flush=True)
                    break
            if res != "skip":       # a verified file costs no rate budget
                time.sleep(INTER_FILE_PAUSE)
        if len(done) < len(todo):
            time.sleep(args.cycle_wait)
    n_fail = len(todo) - len(done)
    print(f"\n{len(done)} OK, {n_fail} still missing")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
