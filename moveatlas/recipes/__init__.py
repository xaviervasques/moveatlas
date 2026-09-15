# -*- coding: utf-8 -*-
"""The recipe tier as library calls: fetch a dataset from its origin host,
harmonize it into the store, then `moveatlas.dataset(id).get_data()`.

    import moveatlas
    moveatlas.fetch("fog_turning_filho")     # origin download, journaled
    moveatlas.ingest("fog_turning_filho")    # canonical records in the store
    recs, meta = moveatlas.dataset("fog_turning_filho").get_data()

A recipe is one of three things, and `moveatlas.recipe(id)` says which:

- LIBRARY: both steps run in Python from this package (the transports in
  moveatlas.recipes.transports, the contract writers such as
  moveatlas.recipes.imu). What a stranger can do from a pip install.
- SCRIPT: the dataset was harmonized by a repository script that is not
  ported yet; fetch()/ingest() raise RecipeIsScript naming the exact
  commands to run from a clone of the repository. Honest, not silent.
- NONE: hosted datasets need no recipe (they download from their
  MoveAtlas record); barrier datasets have a documented route instead.

The store both steps write to is moveatlas.store._repo_root(): the
developer's checkout when MOVEATLAS_REPO points at it, the source tree
when the package sits in one, else ~/.moveatlas/store (MOVEATLAS_STORE).
"""
import os

from moveatlas import registry
from moveatlas.store import _repo_root, user_store_root

__all__ = ["fetch", "ingest", "recipe", "store_root", "RecipeIsScript",
           "NoRecipe"]


class NoRecipe(LookupError):
    """The dataset needs no recipe (hosted or barrier) or is unknown."""


class RecipeIsScript(NotImplementedError):
    """The recipe exists only as repository scripts; the message names them."""


def store_root():
    """The directory whose datasets/ tree fetch() and ingest() fill and
    LocalStore serves (see the module doc)."""
    return _repo_root()


class Recipe:
    """One dataset's recipe. `fetch_fn(root)` and `ingest_fn(root)` are
    library implementations; `fetch_cmd` / `ingest_cmd` are the repository
    commands for a script recipe; `notes` is what a user must know first
    (an account, a licence condition, a size)."""

    def __init__(self, id, fetch_fn=None, ingest_fn=None, fetch_cmd=None,
                 ingest_cmd=None, notes=""):
        self.id = id
        self.fetch_fn, self.ingest_fn = fetch_fn, ingest_fn
        self.fetch_cmd, self.ingest_cmd = fetch_cmd, ingest_cmd
        self.notes = notes

    @property
    def kind(self):
        return "library" if (self.fetch_fn and self.ingest_fn) else "script"

    def describe(self):
        info = registry.dataset_info(self.id)
        lines = [f"{self.id}: {self.kind} recipe ({info['access_case']}; "
                 f"{info['family']}; {info['path']})"]
        if self.notes:
            lines.append(f"  note: {self.notes}")
        if info["access_case"] == "hosted":
            lines.append(f"  served: moveatlas.dataset({self.id!r}).get_data() "
                         "downloads the MoveAtlas record; the recipe below "
                         "rebuilds it from the origin instead")
        if self.kind == "library":
            lines.append(f"  fetch : moveatlas.fetch({self.id!r})")
            lines.append(f"  ingest: moveatlas.ingest({self.id!r})")
        else:
            lines.append(f"  fetch : {self.fetch_cmd or 'see the data card'}")
            lines.append(f"  ingest: {self.ingest_cmd or 'see the data card'}")
        lines.append(f"  card  : {info['path']}/datacard.md")
        return "\n".join(lines)


# -- the library recipes ------------------------------------------------------

def _fetch_fog_turning(root):
    from moveatlas.recipes import transports
    # the atlas ingests the IMU archive and the clinical table; Videos.zip
    # (5 GB of patient video) is never fetched by the library
    return transports.figshare_article(
        root, "datasets/pose/fog_turning_filho", 14984667,
        only=["IMU.zip", "PDFEinfo.csv"])


def _ingest_fog_turning(root):
    import glob
    import zipfile
    import numpy as np
    from moveatlas.recipes import imu
    zips = glob.glob(os.path.join(root, "datasets", "pose", "fog_turning_filho",
                                  "raw", "*.zip"))
    if not zips:
        raise FileNotFoundError("fog_turning_filho: no IMU.zip under raw/; "
                                "run moveatlas.fetch('fog_turning_filho') first")
    z = zipfile.ZipFile(zips[0])
    recs = []
    for n in sorted(x for x in z.namelist() if x.endswith(".txt")):
        ls = [l for l in z.read(n).decode("latin-1").splitlines() if l.strip()]
        a = np.array([[float(v) for v in l.split("\t")] for l in ls[1:]
                      if len(l.split("\t")) >= 7])
        if a.size == 0:
            continue
        # cols: Frame, Time, ACC ML/AP/SI [g], GYR ML/AP [deg/s]
        loc = {"lower_back": {"acc_x": a[:, 2], "acc_y": a[:, 3], "acc_z": a[:, 4],
                              "gyro_x": a[:, 5], "gyro_y": a[:, 6]}}
        subj = os.path.basename(n).split("_")[0]
        recs.append(imu.make_record(loc, 128.0, f"fog_turning:{subj}",
                                    os.path.basename(n)[:-4], "fog_turning_filho"))
    # the records go under the dataset's registry path (datasets/pose/
    # fog_turning_filho), which is where moveatlas.dataset() looks. The
    # repository's own ingestion wrote them under datasets/imu/ (the split
    # folder of 2026-08-23), which the generic loader never found: a
    # library recipe keeps card, raw/ and processed/ together.
    out = imu.save(root, "fog_turning_filho", recs,
                   path="datasets/pose/fog_turning_filho")
    return out, len(recs)


def _fetch_fog_star(root):
    from moveatlas.recipes import transports
    # the sensor table the atlas ingests, the clinical table and the README;
    # the notebook and the environment file stay at the origin
    return transports.zenodo_record(
        root, "datasets/imu/fog_star", 17838806,
        only=["sensor_data.csv", "clinical_data.csv", "README.txt"])


def _ingest_fog_star(root):
    import numpy as np
    from moveatlas.recipes import imu
    try:
        import pandas as pd
    except ImportError as e:
        raise ImportError("fog_star ingestion reads its CSV with pandas: "
                          "pip install pandas") from e
    csv_path = os.path.join(root, "datasets", "imu", "fog_star", "raw",
                            "sensor_data.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError("fog_star: no sensor_data.csv under raw/; "
                                "run moveatlas.fetch('fog_star') first")
    df = pd.read_csv(csv_path)
    locmap = {"ankleL": "ankle_L", "ankleR": "ankle_R", "back": "lower_back",
              "wrist": "wrist_L"}

    def acc_to_g(a):
        # |acc| ~1 means g already, ~9.8 means m/s^2 (the builder's rule);
        # an all-NaN sensor is left as is and make_record drops it
        norm = np.linalg.norm(a, axis=1)
        if not np.isfinite(norm).any():
            return a
        m = np.nanmedian(norm)
        return a / imu.G if m > 5 else a

    recs = []
    for (subj, sess, task), g in df.groupby(["subjectID", "sessionID", "taskID"]):
        loc = {}
        for src, dst in locmap.items():
            acc = acc_to_g(g[[f"{src}_acc_x", f"{src}_acc_y", f"{src}_acc_z"]].values)
            gy = g[[f"{src}_gyro_x", f"{src}_gyro_y", f"{src}_gyro_z"]].values
            loc[dst] = {"acc_x": acc[:, 0], "acc_y": acc[:, 1], "acc_z": acc[:, 2],
                        "gyro_x": gy[:, 0], "gyro_y": gy[:, 1], "gyro_z": gy[:, 2]}
        lab = g["fog"].values if "fog" in g else None
        recs.append(imu.make_record(loc, 60.0, f"fog_star:{subj}",
                                    f"s{sess}_t{task}", "fog_star", lab))
    out = imu.save(root, "fog_star", recs)
    return out, len(recs)


def _fetch_daphnet(root):
    from moveatlas.recipes import transports
    # the UCI archive serves one zip for the whole dataset (CC BY 4.0)
    return transports.urls(
        root, "datasets/imu/daphnet",
        {"daphnet.zip": "https://archive.ics.uci.edu/static/public/245/"
                        "daphnet+freezing+of+gait.zip"})


def _ingest_daphnet(root):
    import glob
    import zipfile
    import numpy as np
    from moveatlas.recipes import imu
    zips = glob.glob(os.path.join(root, "datasets", "imu", "daphnet", "raw", "*.zip"))
    if not zips:
        raise FileNotFoundError("daphnet: no zip under raw/; run "
                                "moveatlas.fetch('daphnet') first")
    z = zipfile.ZipFile(zips[0])
    recs = []
    for n in sorted(x for x in z.namelist() if x.endswith(".txt") and "/S" in "/" + x):
        base = os.path.basename(n)
        if not (base[0] == "S" and "R" in base):
            continue
        a = np.array([[float(v) for v in ln.split()]
                      for ln in z.read(n).decode().splitlines() if ln.strip()])
        if a.size == 0:
            continue
        g = a[:, 1:10] / 1000.0                     # mg -> g; ankle, thigh, trunk
        loc = {"ankle_L": {"acc_x": g[:, 0], "acc_y": g[:, 1], "acc_z": g[:, 2]},
               "thigh_L": {"acc_x": g[:, 3], "acc_y": g[:, 4], "acc_z": g[:, 5]},
               "trunk": {"acc_x": g[:, 6], "acc_y": g[:, 7], "acc_z": g[:, 8]}}
        subj = base[:3]                             # S01
        recs.append(imu.make_record(loc, 64.0, f"daphnet:{subj}", base[:-4],
                                    "daphnet", a[:, 10]))
    out = imu.save(root, "daphnet", recs)
    return out, len(recs)


def _fetch_hd_accel(root):
    from moveatlas.recipes import transports
    # Zenodo 14384260: one CSV per participant plus metadata.csv, CC BY 4.0
    return transports.zenodo_record(root, "datasets/imu/hd_accel_jnet", 14384260)


def _ingest_hd_accel(root):
    import glob
    from moveatlas.recipes import imu
    try:
        import pandas as pd
    except ImportError as e:
        raise ImportError("hd_accel_jnet ingestion reads CSV with pandas: "
                          "pip install pandas") from e
    files = sorted(glob.glob(os.path.join(root, "datasets", "imu", "hd_accel_jnet",
                                          "raw", "*.csv")))
    if not files:
        raise FileNotFoundError("hd_accel_jnet: no CSV under raw/; run "
                                "moveatlas.fetch('hd_accel_jnet') first")
    recs = []
    for f in files:
        b = os.path.basename(f)
        if b.startswith("._") or "metadata" in b:
            continue
        df = pd.read_csv(f)
        if not {"x", "y", "z"} <= set(df.columns):
            continue
        loc = {"wrist_L": {"acc_x": df["x"].values, "acc_y": df["y"].values,
                           "acc_z": df["z"].values}}
        lab = df["label"].values if "label" in df.columns else None
        # the source declares no sampling rate: fps stays None, as in the corpus
        recs.append(imu.make_record(loc, None, f"hd_accel:{b[:-4]}", b[:-4],
                                    "hd_accel_jnet", lab))
    out = imu.save(root, "hd_accel_jnet", recs)
    return out, len(recs)


def _fetch_monipar(root):
    from moveatlas.recipes import transports
    # Zenodo 8104853, CC BY 4.0: the supervised-session .mat the corpus
    # ingests, its labels and the README; the remote and control sessions
    # stay at the origin
    return transports.zenodo_record(
        root, "datasets/imu/monipar", 8104853,
        only=["MONIPAR_PD_SUPERVISED.mat", "MONIPAR_PD_SUPERVISED_TREMOR_LABEL.mat",
              "Monipar_README.txt"])


def _ingest_monipar(root):
    import numpy as np
    from moveatlas.recipes import imu
    try:
        from scipy.io import loadmat
    except ImportError as e:
        raise ImportError("monipar ingestion reads MATLAB files with scipy: "
                          "pip install scipy") from e
    p = os.path.join(root, "datasets", "imu", "monipar", "raw", "MONIPAR_PD_SUPERVISED.mat")
    if not os.path.exists(p):
        raise FileNotFoundError("monipar: no MONIPAR_PD_SUPERVISED.mat under raw/; "
                                "run moveatlas.fetch('monipar') first")
    d = loadmat(p, squeeze_me=True, struct_as_record=False)
    cells = d["SUPERVISED_RAWDATA"]          # (6, 8) cell array of (T, 5)

    def acc_to_g(a):
        norm = np.linalg.norm(a, axis=1)
        if not np.isfinite(norm).any():
            return a
        return a / imu.G if np.nanmedian(norm) > 5 else a

    recs = []
    for i in range(cells.shape[0]):
        for j in range(cells.shape[1]):
            c = np.asarray(cells[i, j])
            if c.ndim != 2 or c.shape[1] < 4 or c.shape[0] < 10:
                continue
            t = c[:, 0]
            dt = np.median(np.diff(t))            # time in ms
            fps = float(1000.0 / dt) if dt > 1e-6 else None
            acc = acc_to_g(c[:, 1:4])
            loc = {"wrist_L": {"acc_x": acc[:, 0], "acc_y": acc[:, 1], "acc_z": acc[:, 2]}}
            lab = c[:, 4] if c.shape[1] >= 5 else None
            recs.append(imu.make_record(loc, fps, f"monipar:sup_r{i}c{j}", f"r{i}c{j}",
                                        "monipar", lab))
    out = imu.save(root, "monipar", recs)
    return out, len(recs)


# -- the script recipes (not ported; the commands are the repository's) -------

_CLONE = "git clone https://github.com/xaviervasques/moveatlas && cd moveatlas"
_SCRIPTS = {
    "ninapro": Recipe(
        "ninapro",
        fetch_cmd="python tools/fetch/fetch_p2_lot.py --only ninapro",
        ingest_cmd="python tools/canonical/build_canonical_emg.py --only ninapro",
        notes="17.6 GB of preprocessed zips; no written licence on the site, "
              "cite Atzori 2014; redistribution stays off"),
    "seizeit2": Recipe(
        "seizeit2",
        fetch_cmd="aws s3 sync --no-sign-request s3://openneuro.org/ds005873 "
                  "datasets/eeg/seizeit2/raw",
        ingest_cmd="python tools/canonical/build_canonical_eeg.py --only seizeit2",
        notes="117.6 GB raw BIDS, CC0; needs the aws CLI"),
    "kaggle_fog": Recipe(
        "kaggle_fog",
        fetch_cmd="Kaggle account: download the competition data into "
                  "datasets/imu/kaggle_fog/raw",
        ingest_cmd="python tools/canonical/build_canonical_imu.py --only kaggle_fog",
        notes="competition data, redistribution restricted"),
    "pd_biostamprc21": Recipe(
        "pd_biostamprc21",
        fetch_cmd="IEEE DataPort (free account): download into "
                  "datasets/imu/pd_biostamprc21/raw",
        ingest_cmd="python tools/ingest/ingest_pd_biostamprc21.py",
        notes="registration required at the source"),
    "amass": Recipe(
        "amass",
        fetch_cmd="AMASS account + EULA: download the SMPL+H archives into "
                  "datasets/socle/amass/raw",
        ingest_cmd="python tools/canonical/build_canonical_amass.py",
        notes="account and EULA at the source; the SMPL+H body model is "
              "needed too"),
    "motion_x": Recipe(
        "motion_x",
        fetch_cmd="Hugging Face download of Motion-X++ into "
                  "datasets/socle/motion_x/raw",
        ingest_cmd="python tools/canonical/build_canonical_motionx.py",
        notes="large public download; licence forbids redistribution"),
    "ntu_rgbd": Recipe(
        "ntu_rgbd",
        fetch_cmd="ROSE Lab portal (application): skeletons into "
                  "datasets/socle/ntu_rgbd/raw",
        ingest_cmd="python tools/canonical/build_canonical_ntu.py",
        notes="application at the source; approved for this project 2026-07-12"),
    "care_pd": Recipe(
        "care_pd",
        fetch_cmd="Hugging Face vida-adl/CARE-PD download into "
                  "datasets/pose/care_pd/raw",
        ingest_cmd="python tools/ingest/extract_care_pd.py, then "
                   "python tools/canonical/build_canonical.py --only care_pd",
        notes="ND licence: harmonized tensors are eval-only and never "
              "redistributed"),
    "goodwin_smm": Recipe(
        "goodwin_smm",
        fetch_cmd="anonymous git clone of the mhealthresearchgroup repository "
                  "into datasets/imu/goodwin_smm/raw",
        ingest_cmd="python tools/ingest/ingest_goodwin_smm.py",
        notes="no data licence exists at the source: internal use only"),
    "koa_pd_nm": Recipe(
        "koa_pd_nm",
        fetch_cmd="direct download (research use) of the videos into "
                  "datasets/pose/koa_pd_nm/raw",
        ingest_cmd="SAM3 segmentation, then "
                   "python tools/canonical/build_canonical_silhouette.py",
        notes="patient video: silhouettes are derived in-house and never "
              "redistributed"),
}

_LIBRARY = {
    "fog_turning_filho": Recipe(
        "fog_turning_filho", fetch_fn=_fetch_fog_turning,
        ingest_fn=_ingest_fog_turning,
        notes="figshare 14984667 (CC BY 4.0): IMU.zip 160 MB + the clinical "
              "table; the 5 GB video archive is not fetched. figshare answers "
              "clients with a browser challenge: fetch() then tells you what "
              "to save where, and accepts the file once it is there"),
    # a hosted dataset can still be rebuilt from its origin: that is what
    # a reviewer checking the harmonization wants, and the recipe is small
    "fog_star": Recipe(
        "fog_star", fetch_fn=_fetch_fog_star, ingest_fn=_ingest_fog_star,
        notes="Zenodo 17838806 (CC BY 4.0): sensor_data.csv 120 MB; also "
              "served from its MoveAtlas record, so get_data() alone works"),
    "daphnet": Recipe(
        "daphnet", fetch_fn=_fetch_daphnet, ingest_fn=_ingest_daphnet,
        notes="UCI archive 245 (CC BY 4.0): one 21 MB zip; also served from "
              "its MoveAtlas record"),
    "hd_accel_jnet": Recipe(
        "hd_accel_jnet", fetch_fn=_fetch_hd_accel, ingest_fn=_ingest_hd_accel,
        notes="Zenodo 14384260 (CC BY 4.0): 35 per-participant CSVs, 124 MB; "
              "also served from its MoveAtlas record"),
    "monipar": Recipe(
        "monipar", fetch_fn=_fetch_monipar, ingest_fn=_ingest_monipar,
        notes="Zenodo 8104853 (CC BY 4.0): the supervised-session MATLAB file, "
              "9 MB, read with scipy; also served from its MoveAtlas record"),
}


def recipe(id):
    """The Recipe for `id`, or raise NoRecipe with the reason."""
    info = registry.dataset_info(id)
    case = info["access_case"]
    if id in _LIBRARY:
        return _LIBRARY[id]
    if id in _SCRIPTS:
        return _SCRIPTS[id]
    if case == "hosted":
        raise NoRecipe(f"{id!r} is hosted: moveatlas.dataset({id!r}).get_data() "
                       "downloads it from its MoveAtlas record; no recipe needed")
    if case == "barrier":
        raise NoRecipe(f"{id!r} is a documented access barrier, not a download. "
                       f"Route on record: {info['access']}. Card: "
                       f"{info['path']}/datacard.md")
    if case == "local_only":
        raise NoRecipe(f"{id!r} is private-tier data; nothing downloads")
    # a recipe dataset with no curated entry: the registry names the
    # script when it knows it, the card otherwise
    from moveatlas.datasets.base import recipe_of
    return Recipe(id, fetch_cmd=f"see the card: {info['path']}/datacard.md "
                                f"(access: {info['access']})",
                  ingest_cmd=recipe_of(info),
                  notes="not ported to the library yet")


def _script(rec, step):
    cmd = rec.fetch_cmd if step == "fetch" else rec.ingest_cmd
    raise RecipeIsScript(
        f"{rec.id!r}: the {step} step is not in the library yet. From a "
        f"clone of the repository ({_CLONE}):\n  {cmd}\n"
        f"{('note: ' + rec.notes) if rec.notes else ''}".rstrip())


def fetch(id, root=None):
    """Download `id` from its origin host into the store's raw/ directory
    (resumable, checksums journaled). Returns what the transport reports."""
    rec = recipe(id)
    if not rec.fetch_fn:
        _script(rec, "fetch")
    return rec.fetch_fn(root or store_root())


def ingest(id, root=None):
    """Harmonize the fetched raw files of `id` into canonical records in
    the store. Returns (output path, number of records)."""
    rec = recipe(id)
    if not rec.ingest_fn:
        _script(rec, "ingest")
    return rec.ingest_fn(root or store_root())
