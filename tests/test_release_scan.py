# -*- coding: utf-8 -*-
"""The leak scan of build_public_release.py, the gate of the public tree.
Corpus-free: each check writes a tiny tree under tmp_path and scans it. The
scanner is loaded from wherever this tree keeps it (the root of the working
tree, tools/release/ in the public tree).

The word lists are sha256 digests, and this file must pass the same scan as
every shipped file, so no listed word appears here in clear: the checks of
the word mechanism add made-up words to the lists, and the strings that must
trip a rule are assembled at run time."""
import importlib.util
import os
import pickle
import re
import shutil

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))


def _load():
    for d in ("", os.path.join("tools", "release")):
        p = os.path.join(REPO, d, "build_public_release.py")
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location("bpr_scan", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod, p
    pytest.skip("build_public_release.py is not in this tree")


@pytest.fixture(scope="module")
def bpr():
    return _load()[0]


def _tree(root, files):
    for rel, text in files.items():
        p = os.path.join(str(root), *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return str(root)


def _kinds(hits):
    return sorted({(sev, rel, kind) for sev, rel, kind, _ev in hits})


ACR = "A" + "I"          # the field's two-letter abbreviation
TITLE = f"  title = {{Using {ACR} to measure Parkinson's disease severity at home}},\n"


def test_word_lists_are_digests_and_the_scanner_passes_its_own_scan(bpr, tmp_path):
    lists = (bpr.VENDOR_SHA256, bpr.MODEL_SHA256, bpr.ACRONYM_SHA256,
             bpr.HELPER_SHA256, bpr.PHRASE_SHA256)
    for lst in lists:
        assert lst and all(re.fullmatch(r"[0-9a-f]{64}", d) for d in lst)
    # the scanner and this test, placed where the public tree ships them
    dst = tmp_path / "tools" / "release"
    dst.mkdir(parents=True)
    shutil.copy(_load()[1], str(dst / "build_public_release.py"))
    (tmp_path / "tests").mkdir()
    shutil.copy(os.path.abspath(__file__), str(tmp_path / "tests" / "test_release_scan.py"))
    assert bpr.scan(str(tmp_path)) == []


def test_a_vendor_token_blocks_also_inside_a_domain(bpr, tmp_path, monkeypatch):
    monkeypatch.setattr(bpr, "VENDOR_SHA256",
                        bpr.VENDOR_SHA256 | {bpr.digest("zyxvendor"),
                                             bpr.digest("zyxtool.sh")})
    root = _tree(tmp_path, {
        "docs/a.md": "Written with ZyxVendor's help.\n",
        "docs/b.md": "See https://www.zyxtool.sh/docs for the editor.\n",
        "docs/c.md": "A zyxtool trajectory and a zyxvendorish word pass.\n",
    })
    assert _kinds(bpr.scan(root)) == [("BLOCK", "docs/a.md", "vendor"),
                                      ("BLOCK", "docs/b.md", "vendor")]


def test_model_and_provenance_words_warn(bpr, tmp_path, monkeypatch):
    monkeypatch.setattr(bpr, "MODEL_SHA256", bpr.MODEL_SHA256 | {bpr.digest("zyxpoem")})
    monkeypatch.setattr(bpr, "HELPER_SHA256", bpr.HELPER_SHA256 | {bpr.digest("zyxhelper")})
    root = _tree(tmp_path, {
        "docs/a.md": "Drafted by Zyxpoem.\n",
        "docs/b.md": "One zyxhelper ran the sweep.\n",
        "docs/c.md": "A user zyxhelper header is not provenance.\n",
        "tools/fetch.py": 'UA = {"User-Agent": "Mozilla/5.0 (moveatlas-fetch)"}\n',
    })
    assert _kinds(bpr.scan(root)) == [("WARN", "docs/a.md", "model"),
                                      ("WARN", "docs/b.md", "attribution")]


def test_the_abbreviation_warns_and_an_allowed_citation_passes(bpr, tmp_path):
    root = _tree(tmp_path, {
        "docs/citations.bib": TITLE,
        "site/source/datasets/park_fingertap.md": TITLE,
        "docs/notes.md": TITLE,
        "tools/ingest.py": "for ai, ax in enumerate('XYZ'):\n    pass\n",
    })
    assert _kinds(bpr.scan(root)) == [("WARN", "docs/notes.md", "acronym")]


FRENCH = ("Le fichier du dossier est la source de la mesure.\n"
          "Les blocs sont detectes par fichier et la position fait foi.\n"
          "La bande annoncee pour le signal est verifiee sur un echantillon.\n")


def test_french_blocks_in_an_authored_document_not_in_a_dataset_page(bpr, tmp_path):
    root = _tree(tmp_path, {
        "docs/mapping.md": "# Mapping\n\n" + FRENCH,
        "site/source/guide.rst": FRENCH,
        "site/gen_page.py": '"""' + FRENCH + '"""\n',
        "site/source/datasets/some_source.md": FRENCH,
        "docs/english.md": "The file of the folder is the source of the measure.\n" * 5,
    })
    assert _kinds(bpr.scan(root)) == [("BLOCK", "docs/mapping.md", "french"),
                                      ("BLOCK", "site/source/guide.rst", "french"),
                                      ("WARN", "site/gen_page.py", "french")]


def test_project_and_backup_drive_paths_warn(bpr, tmp_path):
    bs = "\\"
    root = _tree(tmp_path, {
        "docs/a.md": "runs live under " + "F:" + "/MD_FM/runs\n",
        "docs/b.md": "copied to " + "D:" + bs + "Backup" + bs + "x\n",
        "docs/c.md": "cd " + "/d/" + "MoveAtlas/moveatlas\n",
        "docs/d.md": "https://example.org/d/MoveAtlas and the MD_FM program\n",
    })
    assert _kinds(bpr.scan(root)) == [("WARN", "docs/a.md", "localpath"),
                                      ("WARN", "docs/b.md", "localpath"),
                                      ("WARN", "docs/c.md", "localpath")]


def test_token_shapes_block(bpr, tmp_path):
    root = _tree(tmp_path, {
        "tools/a.py": "TOKEN = '" + "hf_" + "Ab3" * 12 + "'\n",
        "tools/b.py": "TOKEN = '" + "pypi-" + "AgEIcHlwaS5vcmc" * 4 + "'\n",
        "tools/c.py": "KEY = '" + "sk-" + "proj-" + "x9" * 15 + "'\n",
        "tools/d.py": "name = 'hf_dataset'; task = 'mask-" + "y" * 30 + "'\n",
    })
    hits = bpr.scan(root)
    assert _kinds(hits) == [("BLOCK", "tools/a.py", "secret"),
                            ("BLOCK", "tools/b.py", "secret"),
                            ("BLOCK", "tools/c.py", "secret")]
    assert all("redacted" in ev for _s, _r, _k, ev in hits)



# The body-model rule. Its statement patterns are assembled at run time, so
# that this file passes the scan it ships under.
CREDIT = ("MANO/SMPL+H was used for character " + "animation courtesy of the "
          "Max Planck Institute for Intelligent Systems.\n")
RELEASED = "Released for research under the SMPL" + "+H licence.\n"


def _npz(root, rel, **arrays):
    p = os.path.join(str(root), *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    np.savez_compressed(p, **arrays)


def test_body_model_files_their_arrays_and_derived_pages_block(bpr, tmp_path):
    root = _tree(tmp_path, {
        "body_models/smplh/LICENSE.txt": "terms\n",
        "site/source/gallery.rst": "Gallery\n=======\n\n" + CREDIT,
        "docs/notes.md": RELEASED,
        "data/clips.json": '{"J_regressor": [[0.5, 0.5]]}\n',
    })
    _npz(tmp_path, "data/model.npz", v=np.zeros((4, 3)), shapedirs=np.zeros((4, 3, 2)))
    _npz(tmp_path, "data/motion.npz", poses=np.zeros((2, 156)),
         mocap_framerate=np.array(120.0))
    _npz(tmp_path, "assets/SMPLH_male.npz", x=np.zeros(1))
    with open(os.path.join(root, "data", "hands.pkl"), "wb") as f:
        pickle.dump({"hands_componentsl": [[0.0]]}, f)
    assert _kinds(bpr.scan(root)) == [
        ("BLOCK", "assets/SMPLH_male.npz", "bodymodel"),
        ("BLOCK", "body_models/smplh/LICENSE.txt", "bodymodel"),
        ("BLOCK", "data/clips.json", "bodymodel"),
        ("BLOCK", "data/hands.pkl", "bodymodel"),
        ("BLOCK", "data/model.npz", "bodymodel"),
        ("BLOCK", "data/motion.npz", "bodymodel"),
        ("BLOCK", "docs/notes.md", "bodymodel"),
        ("BLOCK", "site/source/gallery.rst", "bodymodel")]


def test_body_model_citations_cards_and_the_amass_builder_pass(bpr, tmp_path):
    root = _tree(tmp_path, {
        "docs/citations.bib": "  title = {Embodied Hands: Modeling and Capturing Hands and "
                              "Bodies Together},\n  note = {SMPL+H, MANO; AMASS},\n",
        "datasets/socle/amass/datacard.md":
            "- Body model: SMPL+H (MANO/SMPL+H licence, non-commercial); to use the data the "
            "SMPL+H and DMPL body models are required; the frame rate is mocap_framerate.\n",
        "tools/canonical/build_canonical_amass.py":
            'm = np.load(os.path.join(REPO, f"body_models/smplh/{g}/model.npz"))\n'
            'v = m["v_template"] + m["shapedirs"] @ betas  # J_regressor, kintree_table\n',
        "tests/test_amass_builder.py": 'd["mocap_framerate"] = np.array(fps)  # dmpls\n',
        "site/searchindex.js": 'Search.setIndex({"terms": {"mocap_framerate": [3]}})\n',
        "docs/datasets_index.csv": "id,notes\namass,SMPL+H body parameters\n",
    })
    _npz(tmp_path, "data/joints.npz", joints=np.zeros((2, 52, 3)), fps=np.array(30.0))
    assert bpr.scan(root) == []
