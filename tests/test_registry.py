# -*- coding: utf-8 -*-
"""The registry: rows, lookup, access-case classification, shipped index."""
import csv
import os

import pytest

from moveatlas import registry
from moveatlas.registry import access_case, dataset_info, list_datasets

ACCESS_CASES = {"hosted", "recipe", "barrier", "local_only"}
EXPECTED_COLUMNS = {"id", "family", "path", "title", "license",
                    "redistribution", "access", "status", "link",
                    "portal_action", "access_case"}
BUNDLED_INDEX = os.path.join(os.path.dirname(registry.__file__), "data",
                             "datasets_index.csv")


# -- list_datasets / dataset_info ------------------------------------------

def test_list_datasets_returns_rows_with_expected_columns():
    rows = list_datasets()
    assert rows, "the registry must not be empty"
    for r in rows:
        missing = EXPECTED_COLUMNS - set(r)
        assert not missing, f"{r.get('id')} lacks columns {sorted(missing)}"
        assert r["access_case"] in ACCESS_CASES


def test_list_datasets_ids_are_unique():
    ids = [r["id"] for r in list_datasets()]
    assert len(ids) == len(set(ids))


def test_list_datasets_filters_by_family_and_case():
    rows = list_datasets()
    fam = rows[0]["family"]
    by_fam = list_datasets(family=fam)
    assert by_fam and all(r["family"] == fam for r in by_fam)
    assert len(by_fam) == sum(r["family"] == fam for r in rows)
    for case in ACCESS_CASES:
        by_case = list_datasets(case=case)
        assert all(r["access_case"] == case for r in by_case)
        assert len(by_case) == sum(r["access_case"] == case for r in rows)
    assert list_datasets(family="no_such_family") == []


def test_dataset_info_known_id():
    first = list_datasets()[0]
    info = dataset_info(first["id"])
    assert info["id"] == first["id"]
    assert info["family"] == first["family"]
    assert info["access_case"] in ACCESS_CASES


def test_dataset_info_unknown_id_lists_known_ids():
    known = sorted(r["id"] for r in list_datasets())
    with pytest.raises(KeyError) as exc:
        dataset_info("no_such_dataset_xyz")
    msg = str(exc.value)
    assert "unknown dataset 'no_such_dataset_xyz'" in msg
    assert "known:" in msg
    assert known[0] in msg and known[-1] in msg


# -- access_case: the four branches -----------------------------------------

@pytest.mark.parametrize("row, expected", [
    ({"license": "private (in-house)", "redistribution": "no",
      "status": "raw on disk"}, "local_only"),
    # private wins over anything else
    ({"license": "Private tier", "redistribution": "yes",
      "status": "DOCUMENTED BARRIER"}, "local_only"),
    # redistributable AND served from a published MoveAtlas record: hosted
    ({"id": "modys_video", "license": "CC BY 4.0", "redistribution": "yes",
      "status": "INGESTED v1"}, "hosted"),
    ({"id": "cody_3", "license": "CC BY-SA 3.0",
      "redistribution": "Yes (share-alike)", "status": ""}, "hosted"),
    # redistributable but no record yet (2026-09-15): fetched at its origin
    ({"id": "fog_turning_filho", "license": "CC0", "redistribution": "yes",
      "status": "INGESTED v1"}, "recipe"),
    ({"license": "CC BY 4.0", "redistribution": "yes",
      "status": "INGESTED v1"}, "recipe"),
    ({"license": "custom", "redistribution": "no",
      "status": "DOCUMENTED BARRIER (owner, 2026-08-28)"}, "barrier"),
    ({"license": "", "redistribution": "no",
      "status": "WRITTEN OFF 2026-08-28: retracted"}, "barrier"),
    ({"license": "", "redistribution": "no",
      "status": "human queue: registration filed"}, "barrier"),
    ({"license": "CC BY-NC-ND 4.0", "redistribution": "NO: ND",
      "status": "INGESTED v1: eval only"}, "recipe"),
    ({"license": "", "redistribution": "", "status": ""}, "recipe"),
    ({}, "recipe"),
    ({"license": None, "redistribution": None, "status": None}, "recipe"),
])
def test_access_case_branches(row, expected):
    assert access_case(row) == expected


def test_access_case_covers_all_four_branches():
    rows = [{"license": "private"},
            {"id": "modys_video", "redistribution": "yes"},
            {"redistribution": "no", "status": "DOCUMENTED BARRIER"},
            {"redistribution": "no", "status": "downloaded"}]
    assert {access_case(r) for r in rows} == ACCESS_CASES


# -- the shipped snapshot ------------------------------------------------------

def test_bundled_index_ships_with_the_package():
    assert os.path.exists(BUNDLED_INDEX)
    assert os.path.exists(os.path.join(os.path.dirname(BUNDLED_INDEX),
                                       "license_matrix.csv"))


def test_every_bundled_row_is_well_formed():
    with open(BUNDLED_INDEX, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows
    seen = set()
    for r in rows:
        for col in ("id", "family", "path"):
            assert (r.get(col) or "").strip(), f"row {r} has empty {col}"
        assert r["id"] not in seen, f"duplicate id {r['id']}"
        seen.add(r["id"])
        assert r["path"].startswith("datasets/"), r["path"]
        assert r["path"].split("/")[1] == r["family"], (r["path"],
                                                        r["family"])
        assert access_case(r) in ACCESS_CASES


# -- resolution order: MOVEATLAS_REPO wins ---------------------------------

def test_registry_reads_docs_under_moveatlas_repo(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "datasets_index.csv").write_text(
        "id,family,path,title,redistribution,access,status,link\n"
        "toy_a,imu,datasets/imu/toy_a,Toy A,yes,download,INGESTED,http://a\n"
        "toy_b,pose,datasets/pose/toy_b,Toy B,no,email,DOCUMENTED BARRIER,"
        "http://b\n", encoding="utf-8")
    (docs / "license_matrix.csv").write_text(
        "id,license,redistribution,portal_action\n"
        "toy_a,CC BY 4.0,yes,host_copy_ok\n", encoding="utf-8")
    monkeypatch.setenv("MOVEATLAS_REPO", str(tmp_path))
    rows = {r["id"]: r for r in list_datasets()}
    assert set(rows) == {"toy_a", "toy_b"}
    # license filled from the matrix when the index has no license column
    assert rows["toy_a"]["license"] == "CC BY 4.0"
    assert rows["toy_a"]["portal_action"] == "host_copy_ok"
    # redistributable, but toy_a has no published record: fetched at origin
    assert rows["toy_a"]["access_case"] == "recipe"
    assert rows["toy_b"]["license"] == ""
    assert rows["toy_b"]["access_case"] == "barrier"
    assert dataset_info("toy_b")["title"] == "Toy B"
    with pytest.raises(KeyError, match="known: toy_a, toy_b"):
        dataset_info("toy_c")


def test_registry_raises_when_no_index_anywhere(tmp_path, monkeypatch):
    monkeypatch.setenv("MOVEATLAS_REPO", str(tmp_path))
    monkeypatch.setattr(registry, "_HERE", str(tmp_path / "nowhere"))
    with pytest.raises(FileNotFoundError, match="MOVEATLAS_REPO"):
        list_datasets()
