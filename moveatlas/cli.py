# -*- coding: utf-8 -*-
"""The `moveatlas` command line: the same verbs as the library.

    moveatlas list [--family imu] [--case hosted|recipe|barrier]
    moveatlas info <id>
    moveatlas fetch <id>
    moveatlas ingest <id>
    moveatlas files <id>
    moveatlas get <id> <file name>
    moveatlas where
"""
import argparse
import sys

import moveatlas
from moveatlas import recipes, registry


def cmd_list(a):
    rows = registry.list_datasets(family=a.family or None, case=a.case or None)
    w = max((len(r["id"]) for r in rows), default=8)
    print(f"{'id':{w}s}  {'family':9s}  {'case':8s}  title")
    for r in rows:
        print(f"{r['id']:{w}s}  {r['family']:9s}  {r['access_case']:8s}  "
              f"{r['title'][:60]}")
    print(f"{len(rows)} datasets")


def cmd_info(a):
    r = registry.dataset_info(a.id)
    for k in ("id", "title", "family", "access_case", "license",
              "redistribution", "access", "path"):
        print(f"{k:14s} {r.get(k, '')}")
    table = registry.records_table().get(a.id)
    if table:
        print(f"{'record':14s} https://doi.org/{table['doi']}")
    try:
        print(recipes.recipe(a.id).describe())
    except recipes.NoRecipe as e:
        print(f"{'recipe':14s} none: {e}")


def cmd_fetch(a):
    out = recipes.fetch(a.id)
    for name, n, sha in out:
        print(f"  {name}  {n} bytes  {sha[:12]}")
    print(f"{a.id}: {len(out)} file(s) in {recipes.store_root()}")


def cmd_ingest(a):
    out, n = recipes.ingest(a.id)
    print(f"{a.id}: {n} records -> {out}")


def cmd_files(a):
    ds = moveatlas.dataset(a.id)
    files = ds.files()
    for f in files:
        print(f)
    print(f"{len(files)} file(s); moveatlas get {a.id} <name> fetches one")


def cmd_get(a):
    print(moveatlas.dataset(a.id).path(a.name))


def cmd_where(a):
    print(recipes.store_root())


def main(argv=None):
    ap = argparse.ArgumentParser(prog="moveatlas",
                                 description=__doc__.splitlines()[0])
    ap.add_argument("--version", action="version",
                    version=f"moveatlas {moveatlas.__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="the catalogue, with each access case")
    p.add_argument("--family", default="")
    p.add_argument("--case", default="",
                   choices=["", "hosted", "recipe", "barrier", "local_only"])
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("info", help="one dataset: registry row, record, recipe")
    p.add_argument("id")
    p.set_defaults(fn=cmd_info)
    p = sub.add_parser("fetch", help="download a recipe dataset from its origin")
    p.add_argument("id")
    p.set_defaults(fn=cmd_fetch)
    p = sub.add_parser("ingest", help="harmonize a fetched dataset into the store")
    p.add_argument("id")
    p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("files", help="list the files a dataset holds")
    p.add_argument("id")
    p.set_defaults(fn=cmd_files)
    p = sub.add_parser("get", help="a local, verified path to one file of a dataset")
    p.add_argument("id")
    p.add_argument("name")
    p.set_defaults(fn=cmd_get)
    p = sub.add_parser("where", help="print the store directory")
    p.set_defaults(fn=cmd_where)
    a = ap.parse_args(argv)
    try:
        a.fn(a)
    except (recipes.NoRecipe, recipes.RecipeIsScript, FileNotFoundError,
            LookupError) as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
