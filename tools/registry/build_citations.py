# -*- coding: utf-8 -*-
"""Resolve a formal citation for every dataset in the catalogue.

Written 2026-08-23. The repo carried a bare `link` per dataset and nothing else:
no DOI, no authors, no year, no venue, and no .bib anywhere. A resource paper has
to cite every dataset it builds on, so this was a publication blocker hiding in
plain sight.

What it does: derive a DOI from each dataset's link where the host allows it, then
resolve that DOI to real metadata and write both a BibTeX file and a machine
readable CSV. Nothing is invented: a dataset whose citation cannot be established
is listed as UNRESOLVED for a human to fill, never guessed at from the title.

Two citations are kept where both exist, because they are different objects and a
resource paper generally owes both:
  data   the deposit itself (figshare, Zenodo, Mendeley, OpenNeuro, PhysioNet)
  paper  the accompanying article, when the deposit names one

Hosts resolved automatically:
  doi.org / dx.doi.org      Crossref first, then DataCite
  zenodo.org                Zenodo API -> DOI, authors, year
  figshare.com              figshare API -> DOI, authors, plus resource_doi (paper)
  openneuro.org             DOI is 10.18112/openneuro.<accession>, via DataCite
  data.mendeley.com         DOI is 10.17632/<id>, via DataCite
  physionet.org             the project page carries its own DOI, parsed from it
  datadryad.org             DOI parsed from the dataset path
  osf.io                    OSF API
  arxiv.org                 arXiv API

Env: /Users/xavi/.venvs/kinefm. Usage:
    python build_citations.py [--repo PATH] [--only id1,id2] [--refresh]

Results are cached in docs/_citation_cache.json so a re-run costs no network.
"""
import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

# a DOI as it appears in free text; the class is built from chars rather
# than written inline to keep the quoting sane
DOI_RE = r"(10\.\d{4,9}/[^\s\'\"<>)\]]+)"

HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 "
                     "Safari/537.36 MoveAtlas-citations/1.0 (mailto:noreply@example.org)",
       "Accept": "application/json"}


def get_json(url, timeout=45):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HDR),
                                timeout=timeout) as r:
        return json.load(r)


def doi_resolves(doi, timeout=30):
    """True when doi.org answers a redirect for the DOI (no content
    negotiation: OpenNeuro DOIs resolve without any CSL record)."""
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(urllib.request.Request(
            "https://doi.org/" + urllib.parse.quote(doi, safe="/:()"),
            method="HEAD", headers=HDR), timeout=timeout)
        return True
    except urllib.error.HTTPError as e:
        return e.code in (301, 302, 303, 307, 308)
    except Exception:
        return False


def get_text(url, timeout=45):
    with urllib.request.urlopen(urllib.request.Request(
            url, headers=dict(HDR, Accept="text/html,*/*")), timeout=timeout) as r:
        return r.read().decode("utf8", "replace")


# --------------------------------------------------------------- DOI resolution
def from_crossref(doi):
    d = get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")["message"]
    authors = [f"{a.get('family','')}, {a.get('given','')}".strip(", ")
               for a in d.get("author", []) if a.get("family") or a.get("given")]
    year = ""
    for k in ("published-print", "published-online", "issued", "created"):
        p = d.get(k, {}).get("date-parts", [[None]])[0]
        if p and p[0]:
            year = str(p[0]); break
    return {"doi": d.get("DOI", doi), "title": (d.get("title") or [""])[0],
            "authors": authors, "year": year,
            "venue": (d.get("container-title") or [""])[0],
            "publisher": d.get("publisher", ""), "type": d.get("type", ""),
            "source": "crossref"}


def from_datacite(doi):
    d = get_json(f"https://api.datacite.org/dois/{urllib.parse.quote(doi)}")["data"]["attributes"]
    authors = []
    for a in d.get("creators", []):
        n = a.get("name") or f"{a.get('familyName','')}, {a.get('givenName','')}"
        if n.strip(", "):
            authors.append(n.strip(", "))
    return {"doi": d.get("doi", doi), "title": (d.get("titles") or [{}])[0].get("title", ""),
            "authors": authors, "year": str(d.get("publicationYear") or ""),
            "venue": d.get("publisher", "") if isinstance(d.get("publisher"), str)
                     else (d.get("publisher") or {}).get("name", ""),
            "publisher": d.get("publisher", "") if isinstance(d.get("publisher"), str)
                     else (d.get("publisher") or {}).get("name", ""),
            "type": (d.get("types") or {}).get("resourceTypeGeneral", "Dataset"),
            "source": "datacite"}


def _no_email(author):
    s = re.sub(r"\(?\s*[\w.+-]+@[\w-]+(\.[\w-]+)+\s*\)?", "", author)
    return re.sub(r"\s+", " ", s).strip(" ,;")


def from_bids(acc, path=None):
    """Citation straight out of a local BIDS dataset_description.json.

    OpenNeuro DOIs are NOT registered with Crossref or DataCite (checked
    2026-08-23: both return 404 for ds004584 and ds007526), so the dataset's own
    declaration is the authoritative source and it is already on disk.
    """
    # the dataset folder is NOT always named after its accession (seizeit2 holds
    # ds005873), so the catalogue path is checked first and the accession scan is
    # only the fallback.
    cands = []
    if path:
        cands.append(path)
    for base in ("datasets/eeg", "datasets/pose", "datasets/imu", "datasets/socle"):
        if os.path.isdir(base):
            cands += [os.path.join(base, d) for d in os.listdir(base) if acc in d]
    for d in cands:
            dd = os.path.join(d, "raw", "dataset_description.json")
            if not os.path.exists(dd):
                continue
            try:
                # explicit utf-8: on Windows the default is cp1252 and ds005873's
                # description (curly quotes in the acknowledgements) failed to
                # parse, which silently cost the whole citation (found 2026-08-23)
                j = json.load(open(dd, encoding="utf-8-sig"))
            except Exception:
                continue
            year = ""
            ch = os.path.join(d, "raw", "CHANGES")
            if os.path.exists(ch):
                try:
                    y = re.search(r"(20\d{2})-\d{2}-\d{2}",
                                  open(ch, encoding="utf-8-sig",
                                       errors="replace").read())
                    if y:
                        year = y.group(1)
                except Exception:
                    pass
            declared = (j.get("DatasetDOI") or "").replace("doi:", "").strip()
            doi = declared
            source = "bids dataset_description.json"
            if declared and not doi_resolves(declared):
                # ds007526 declares .v1.0.2 while only .v1.0.0 is registered
                # (2026-09-08): keep the citation resolvable, say so
                first = re.sub(r"\.v[\d.]+$", ".v1.0.0", declared)
                if first != declared and doi_resolves(first):
                    doi = first
                    ver = declared.rsplit(".v", 1)[-1]
                    source = (f"bids dataset_description.json (declares v{ver}; "
                              "only the v1.0.0 DOI is registered - checked on "
                              f"doi.org {time.strftime('%Y-%m-%d')})")
                    print(f"  {acc}: declared DOI {declared} does not resolve; "
                          f"citing {first}", flush=True)
            return {"doi": doi,
                    "title": j.get("Name", "") or acc,
                    # BIDS author strings sometimes carry the e-mail address
                    # ("Arun Singh arun.singh@usd.edu", "Inbal Maidan
                    # (inbalm@...)"): a citation names people, it does not
                    # republish their addresses (2026-09-17)
                    "authors": [a for a in (_no_email(x) for x in
                                            j.get("Authors", []) if x) if a],
                    "year": year, "venue": "OpenNeuro", "publisher": "OpenNeuro",
                    "type": "Dataset", "source": source}
    return None


def resolve_doi(doi):
    doi = doi.strip().rstrip(".").replace("https://doi.org/", "").replace(
        "http://dx.doi.org/", "").replace("https://dx.doi.org/", "")
    for fn in (from_crossref, from_datacite):
        try:
            m = fn(doi)
            if m.get("title"):
                return m
        except Exception:
            continue
    return None


# ------------------------------------------------------- per-host DOI discovery
def doi_from_link(link):
    """Return (data_doi, paper_doi). Either may be None."""
    l = (link or "").strip()
    if not l:
        return None, None
    m = re.search(r"(?:doi\.org/|dx\.doi\.org/)(10\.[^\s?#]+)", l)
    if m:
        return m.group(1), None
    if "zenodo.org" in l:
        m = re.search(r"records?/(\d+)", l)
        if m:
            try:
                d = get_json(f"https://zenodo.org/api/records/{m.group(1)}")
                return d.get("doi"), None
            except Exception:
                return f"10.5281/zenodo.{m.group(1)}", None
    if "figshare.com" in l:
        m = re.search(r"\.(\d{6,})(?:\.v\d+)?/?$", l) or re.search(r"/(\d{6,})", l)
        if m:
            try:
                d = get_json(f"https://api.figshare.com/v2/articles/{m.group(1)}")
                return d.get("doi"), d.get("resource_doi")
            except Exception:
                pass
    if "openneuro.org" in l:
        m = re.search(r"(ds\d{6})", l)
        if m:
            acc = m.group(1)
            # the DOI carries the dataset VERSION, which is not guessable. Prefer
            # the local BIDS dataset_description.json when the set is on disk,
            # then fall back to a DataCite search for the accession.
            # CAVEAT (2026-09-08): a dataset_description.json can declare a
            # snapshot DOI that was never registered (ds007526 declares
            # v1.0.2; only .v1.0.0 resolves on doi.org). Whatever DOI is
            # chosen, callers must check it resolves (doi_resolves below)
            # and fall back to the .v1.0.0 form, which OpenNeuro always
            # registers at first publication.
            try:
                q = get_json("https://api.datacite.org/dois?query="
                             + urllib.parse.quote(f"openneuro.{acc}") + "&page[size]=5")
                for it in q.get("data", []):
                    doi = it.get("attributes", {}).get("doi", "")
                    if acc in doi:
                        return doi, None
            except Exception:
                pass
            return None, None
    if "data.mendeley.com" in l:
        m = re.search(r"datasets/(\w+)", l)
        if m:
            return f"10.17632/{m.group(1)}.1", None
    if "datadryad.org" in l:
        m = re.search(r"(10\.5061/dryad\.[\w.]+)", l)
        if m:
            return m.group(1), None
    if "physionet.org" in l:
        m = re.search(r"content/([\w.-]+)", l)
        if m:
            try:
                h = get_text(f"https://physionet.org/content/{m.group(1)}/")
                d = re.search(r"(10\.13026/[\w.-]+)", h)
                p = re.search(r"(10\.(?!13026)[\w.]+/[^\s\"<)]+)", h)
                return (d.group(1) if d else None), (p.group(1) if p else None)
            except Exception:
                pass
    if "osf.io" in l:
        m = re.search(r"osf\.io/(\w+)", l)
        if m:
            return f"10.17605/OSF.IO/{m.group(1).upper()}", None
    if "arxiv.org" in l:
        m = re.search(r"(\d{4}\.\d{4,5})", l)
        if m:
            return None, f"10.48550/arXiv.{m.group(1)}"
    if "github.com" in l:
        m = re.match(r"https?://github\.com/([^/]+)/([^/#?]+)", l)
        if m:
            owner, repo = m.group(1), m.group(2).rstrip("/")
            # a well-kept repo declares its citation; otherwise the README usually
            # carries the paper DOI or an arXiv id
            for path in ("CITATION.cff", "README.md"):
                try:
                    txt = get_text(f"https://raw.githubusercontent.com/{owner}/"
                                   f"{repo}/HEAD/{path}")
                except Exception:
                    continue
                d = re.search(DOI_RE, txt)
                if d:
                    return None, d.group(1).rstrip(".,;")
                a = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", txt)
                if a:
                    return None, f"10.48550/arXiv.{a.group(1)}"
    if "huggingface.co" in l:
        m = re.match(r"https?://huggingface\.co/datasets/([^/#?]+/[^/#?]+)", l)
        if m:
            try:
                txt = get_text(f"https://huggingface.co/datasets/{m.group(1)}/raw/main/README.md")
                d = re.search(DOI_RE, txt)
                if d:
                    return None, d.group(1).rstrip(".,;")
            except Exception:
                pass
    if "archive.ics.uci.edu" in l or "hbiostat.org" in l or "data.bris.ac.uk" in l \
            or "data.4tu.nl" in l or "physionet.org" in l or "ora.ox.ac.uk" in l \
            or "brain-development.org" in l or "rose1.ntu.edu.sg" in l:
        # last resort that is still EVIDENCE rather than guesswork: read the
        # dataset's own landing page and take a DOI it prints itself.
        try:
            txt = get_text(l)
            found = re.findall(DOI_RE, txt)
            own = [d for d in found if d.startswith(("10.24432", "10.13026", "10.5523",
                                                     "10.4121", "10.5287"))]
            if own:
                return own[0].rstrip(".,;)"), (found[0].rstrip(".,;)")
                                               if found and found[0] not in own else None)
            if found:
                return None, found[0].rstrip(".,;)")
        except Exception:
            pass
    if "nature.com/articles/" in l:
        m = re.search(r"articles/([\w-]+)", l)
        if m:
            return None, f"10.1038/{m.group(1)}"
    return None, None


def crossref_candidates(title, n=2):
    """Top Crossref hits for a dataset title. NOT accepted automatically: these are
    SUGGESTIONS for a human to confirm, because a title search can land on a paper
    that merely uses the dataset rather than the one that published it."""
    try:
        q = get_json("https://api.crossref.org/works?rows=%d&query.bibliographic=%s"
                     % (n, urllib.parse.quote(title[:180])))
        out = []
        for it in q.get("message", {}).get("items", []):
            au = [f"{a.get('family','')}, {a.get('given','')}".strip(", ")
                  for a in it.get("author", [])][:4]
            yr = ""
            for k in ("published-print", "published-online", "issued"):
                d = it.get(k, {}).get("date-parts", [[None]])[0]
                if d and d[0]:
                    yr = str(d[0]); break
            out.append({"doi": it.get("DOI", ""), "title": (it.get("title") or [""])[0],
                        "authors": au, "year": yr,
                        "venue": (it.get("container-title") or [""])[0],
                        "score": round(it.get("score", 0), 1)})
        return out
    except Exception:
        return []


def bibkey(ds_id, meta, kind):
    y = meta.get("year") or "n.d."
    return f"{ds_id}_{kind}_{y}"


def to_bibtex(key, meta, kind):
    entry = "misc" if kind == "data" else "article"
    fields = [("title", meta.get("title", "")),
              ("author", " and ".join(meta.get("authors", [])) or "{Unknown}"),
              ("year", meta.get("year", "")),
              ("doi", meta.get("doi", "")),
              ("howpublished" if entry == "misc" else "journal",
               meta.get("venue") or meta.get("publisher", "")),
              ("note", "dataset" if kind == "data" else "")]
    body = ",\n  ".join(f"{k} = {{{v}}}" for k, v in fields if v)
    return f"@{entry}{{{key},\n  {body}\n}}\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--only", default=None,
                    help="re-resolve these ids (ignoring their cache entry); "
                         "the outputs still cover the whole registry")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache")
    args = ap.parse_args()

    idx = os.path.join(args.repo, "docs", "datasets_index.csv")
    rows = list(csv.DictReader(open(idx)))
    # --only used to FILTER the rows, so the files below were rewritten
    # with those ids alone and every other citation vanished (found
    # 2026-09-17 before a run). It now only selects what is re-resolved.
    want = {x.strip() for x in args.only.split(",")} if args.only else None

    # Hand-verified DOIs that no automatic route can find, usually because the
    # dataset's link is a bare domain. Each row carries its evidence, and only
    # exact title matches were accepted; a plausible-looking hit is not enough.
    overrides = {}
    ov = os.path.join(args.repo, "docs", "citation_overrides.csv")
    if os.path.exists(ov):
        with open(ov, newline="", encoding="utf8") as f:
            for row in csv.DictReader(f):
                if row.get("dataset") and row.get("doi"):
                    overrides[(row["dataset"], row.get("kind") or "paper")] = row["doi"]

    cache_path = os.path.join(args.repo, "docs", "_citation_cache.json")
    cache = {} if args.refresh or not os.path.exists(cache_path) \
        else json.load(open(cache_path))

    out, unresolved = [], []
    for i, r in enumerate(rows, 1):
        ds = r["id"]
        if want is not None and ds not in want:
            rec = cache.get(ds)
            if rec is None:
                print(f"  {ds}: not in the cache and not asked for; left out")
                continue
            out.append(rec)
            if not (rec.get("data") or rec.get("paper")):
                unresolved.append((ds, r["link"], rec.get("candidates") or []))
            continue
        if ds in cache and want is None:
            rec = cache[ds]
        else:
            rec = {"id": ds, "link": r["link"], "data": None, "paper": None}
            try:
                d_doi, p_doi = doi_from_link(r["link"])
            except Exception:
                d_doi = p_doi = None
            d_doi = overrides.get((ds, "data"), d_doi)
            p_doi = overrides.get((ds, "paper"), p_doi)
            for kind, doi in (("data", d_doi), ("paper", p_doi)):
                if doi:
                    m = resolve_doi(doi)
                    if m:
                        rec[kind] = m
            if not rec["data"]:
                acc = re.search(r"(ds\d{6})", r["link"] or "")
                if acc:
                    m = from_bids(acc.group(1), r.get("path"))
                    if m and m.get("authors"):
                        rec["data"] = m
            cache[ds] = rec
            time.sleep(0.3)                    # be polite to the DOI APIs
        got = [k for k in ("data", "paper") if rec.get(k)]
        print(f"[{i:3d}/{len(rows)}] {ds:28s} {'+'.join(got) if got else 'UNRESOLVED'}",
              flush=True)
        if not got:
            cands = rec.get("candidates")
            if cands is None:
                cands = crossref_candidates(r.get("title") or ds)
                rec["candidates"] = cands
                cache[ds] = rec
                time.sleep(0.3)
            unresolved.append((ds, r["link"], cands))
        out.append(rec)
        if i % 10 == 0:
            json.dump(cache, open(cache_path, "w"), indent=1)
    json.dump(cache, open(cache_path, "w"), indent=1)

    bib_path = os.path.join(args.repo, "docs", "citations.bib")
    csv_path = os.path.join(args.repo, "docs", "citations.csv")
    with open(bib_path, "w", encoding="utf8") as f:
        f.write("% Citations for every dataset in the MoveAtlas catalogue.\n"
                "% Generated by build_citations.py; DOIs resolved through Crossref\n"
                "% and DataCite. 'data' entries cite the deposit, 'paper' entries the\n"
                "% accompanying article. Datasets absent from this file could not be\n"
                "% resolved automatically and are listed in citations.csv as UNRESOLVED.\n\n")
        for rec in out:
            for kind in ("data", "paper"):
                m = rec.get(kind)
                if m:
                    f.write(to_bibtex(bibkey(rec["id"], m, kind), m, kind) + "\n")
    with open(csv_path, "w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow(["dataset", "kind", "doi", "year", "authors", "title", "venue",
                    "bibkey", "resolved_via"])
        for rec in out:
            wrote = False
            for kind in ("data", "paper"):
                m = rec.get(kind)
                if m:
                    w.writerow([rec["id"], kind, m.get("doi", ""), m.get("year", ""),
                                "; ".join(m.get("authors", []))[:300],
                                m.get("title", "")[:220],
                                m.get("venue") or m.get("publisher", ""),
                                bibkey(rec["id"], m, kind), m.get("source", "")])
                    wrote = True
            if not wrote:
                w.writerow([rec["id"], "UNRESOLVED", "", "", "", "", "",
                            "", f"link: {rec.get('link','')}"])

    n_data = sum(1 for r in out if r.get("data"))
    n_paper = sum(1 for r in out if r.get("paper"))
    print(f"\n{len(out)} datasets: {n_data} with a data citation, {n_paper} with a "
          f"paper citation, {len(unresolved)} unresolved")
    print(f"-> {os.path.relpath(bib_path, args.repo)} and "
          f"{os.path.relpath(csv_path, args.repo)}")
    cand_path = os.path.join(args.repo, "docs", "citation_candidates.md")
    if unresolved:
        with open(cand_path, "w", encoding="utf8") as f:
            f.write("# Datasets whose citation could not be resolved automatically\n\n"
                    "Generated by build_citations.py. Each entry lists the top Crossref\n"
                    "hits for the dataset TITLE. These are SUGGESTIONS, not answers: a\n"
                    "title search can land on a paper that merely uses a dataset rather\n"
                    "than the one that published it. Confirm before citing, then add the\n"
                    "DOI to the dataset's entry in gen_datacards.py.\n\n"
                    "A dataset with no candidate at all usually means its `link` in\n"
                    "docs/datasets_index.csv is a bare domain with no path, which is its\n"
                    "own defect worth fixing.\n\n")
            for ds, link, cands in unresolved:
                f.write(f"## {ds}\n\nlink: `{link}`\n\n")
                if not cands:
                    f.write("_no candidate found_\n\n")
                for c in cands:
                    f.write(f"- **{c['title'][:150]}** ({c['year']}), "
                            f"{c['venue'][:60]}  \n  doi: `{c['doi']}` · "
                            f"score {c['score']} · {'; '.join(c['authors'])[:120]}\n")
                f.write("\n")
        print(f"\nUNRESOLVED: {len(unresolved)} datasets. Candidate matches written to "
              f"{os.path.relpath(cand_path, args.repo)}")
        for ds, link, cands in unresolved:
            print(f"   {ds:28s} {len(cands)} candidate(s)  {link[:50]}")


if __name__ == "__main__":
    main()
