#!/usr/bin/env python3
"""
Rebuild datasets/_catalogue.csv from the on-disk state crossed with dataset
metadata. Idempotent, re-run any time to refresh statuses after downloads.

Status is derived from disk:
    a_telecharger    raw/ and processed/ both empty
    telecharge_brut  raw/ populated, processed/ empty
    traite           processed/ populated

'acces' flags how the data is obtained; gated sets carry their landing page in
'lien_manuel' so a human can fetch them (Synapse token, IEEE login, lab form).

Run inside 'atlas-mouvement':  python build_catalogue.py
"""
import os, csv

ROOT = "datasets"

# (modalite, jeu, nom, dossier_sub, nouveau, alimente_fm, acces, lien_manuel, note)
# acces: direct | mendeley | zenodo | physionet | git | synapse | ieee | form | request
CAT = [
 ("pose","li_taati","Parkinson's Pose Estimation (Li/Taati)","pose/li_taati","non","oui","git","","2D pixels; ingere 776 recs; toe tapping=flux optique separe"),
 ("pose","care_pd","CARE-PD","pose/care_pd","non","oui","request","https://github.com/TaatiTeam/CARE-PD","9 cohortes; traite 24 joints 3D; NC certain, ND a clarifier"),
 ("pose","visionmd","VisionMD (outil+demo)","pose/visionMD","non","non","git","","outil, pas un corpus; n'alimente pas le FM"),
 ("pose","toronto_neuroface","Toronto NeuroFace","pose/toronto_neuroface","non","oui","request","https://slp.utoronto.ca/faculty/yana-yunusova/speech-production-lab/datasets/","GATED: demande au labo Yunusova (UofT); orofacial 36 sujets"),
 ("pose","modys_video","MODYS-video (Haberfehlner)","pose/modys_video","OUI","oui","zenodo","","Zenodo 5638470; stick-figure choree/dystonie pediatrique"),
 ("pose","koa_pd_nm","KOA-PD-NM","pose/koa_pd_nm","OUI","oui","direct","","3.8Go; .rar NON extrait (installer unar/unrar)"),
 ("pose","gavd","GAVD (Gait Abnormality Video)","pose/gavd","OUI","oui","git","","annotations pose marche pathologique"),
 ("pose","park_fingertap","PARK finger-tapping (ROC-HCI)","pose/park_fingertap","OUI","oui","git","","features seules"),
 ("pose","ataxie_kinect_dib","Ataxie marche Kinect (Data in Brief)","pose/ataxie_kinect_dib","OUI","oui","direct","","supp. mmc1.xlsx (Summa 2020, DOI 10.1016/j.dib.2020.106307)"),
 ("pose","fog_turning_filho","FoG Turning-In-Place (Filho 2022)","pose/fog_turning_filho","OUI","oui","direct","","figshare; pose + IMU"),
 ("pose","tim_tremor","TIM-TREMOR","pose/tim_tremor","non","oui","request","https://data.4tu.nl","dossier vide; video->pose via SAM3; retire du catalogue-40"),
 ("imu","weargait_pd","WearGait-PD (Sci Data 2026)","imu/weargait_pd","non","oui","synapse","https://www.synapse.org/Synapse:syn52540892","GATED: token Synapse; 13 IMU + semelles, 100 PD/85 ctrl"),
 ("imu","pads","PADS Parkinson smartwatch","imu/pads","OUI","oui","physionet","","re-telechargement en cours (735Mo complet)"),
 ("imu","kaggle_fog","Kaggle tlVMC Freezing of Gait","imu/kaggle_fog","non","oui","direct","","62Go zip NON extrait"),
 ("imu","daphnet","Daphnet Freezing of Gait","imu/daphnet","non","oui","direct","","CC BY 4.0 UCI; 3 accel 64Hz"),
 ("imu","pd_biostamprc21","PD-BioStampRC21","imu/pd_biostamprc21","non","oui","ieee","https://ieee-dataport.org/open-access/pd-biostamprc21-parkinsons-disease-accelerometry-dataset-five-wearable-sensor-study-0","GATED: compte IEEE gratuit; 10.8Go, 5 capteurs, 34 sujets"),
 ("imu","physionet_gaitpdb","PhysioNet gaitpdb","imu/physionet_gaitpdb","non","oui","physionet","","PD/Huntington/SLA force marche"),
 ("imu","accel_fluctuations","Accelerometrie fluctuations motrices / MJFF Levodopa (Sci Data)","imu/accel_fluctuations","non","oui","synapse","https://www.synapse.org/Synapse:syn20681023","GATED: Synapse + certification + data-use statement"),
 ("imu","gaitndd","gaitndd (Neurodegenerative Gait)","imu/gaitndd","OUI","oui","physionet","","force gait"),
 ("imu","hd_accel_jnet","Accelerometrie Huntington (J-Net)","imu/hd_accel_jnet","OUI","oui","zenodo","","Zenodo 14384260; choree HD"),
 ("imu","clinical_gait_multipatho","Clinical Gait Signals wearable (figshare)","imu/clinical_gait_multipatho","OUI","oui","direct","","2Go multi-pathologie"),
 ("imu","imu_inthewild_iprognosis","IMU in-the-wild PD (Zenodo 3519213)","imu/imu_inthewild_iprognosis","OUI","oui","zenodo","","1.8Go phonecalls IMU"),
 ("imu","monipar","Monipar smartwatch PD (Zenodo)","imu/monipar","OUI","oui","zenodo","","Zenodo 8104853; tremor labels"),
 ("imu","tremordb","tremordb (DBS parkinsonian tremor)","imu/tremordb","OUI","oui","physionet","","tremblement"),
 ("imu","gaitdb","gaitdb (Gait in Aging and Disease)","imu/gaitdb","OUI","oui","physionet","","force gait"),
 ("imu","alameda_tremor","ALAMEDA PD Tremor (Zenodo)","imu/alameda_tremor","OUI","oui","zenodo","","Zenodo 10782573; tremblement PD"),
 ("imu","fog_star","FoG-STAR (Sci Data 2026)","imu/fog_star","OUI","oui","zenodo","","Zenodo 17838806; 22 PD, 4 IMU, 101 episodes FoG"),
 ("imu","multimodal_fog","Multimodal FoG (Mendeley r8gmbtv7w2)","imu/multimodal_fog","OUI","oui","mendeley","","v3, 58 fichiers ~3.9Go; IMU+EEG"),
 ("socle","amass","AMASS","socle/amass","non","socle","form","https://amass.is.tue.mpg.de","GATED: compte/EULA par sous-base; mocap SMPL sain"),
 ("socle","motion_x","Motion-X","socle/motion_x","non","socle","form","https://github.com/IDEA-Research/Motion-X","GATED: Google Form; mouvement-langage"),
 ("socle","vidimu","VIDIMU (Sci Data 2023)","socle/vidimu","OUI","socle","zenodo","","Zenodo 15075076; data+analysis+small video (full 41Go exclu)"),
 ("socle","capture24","Capture-24 (Oxford)","socle/capture24","OUI","socle","direct","","ORA; 151 sujets poignet AX3, labels camera (6.4Go)"),
 ("socle","ntu_rgbd","NTU RGB+D / 120","socle/ntu_rgbd","non","socle","form","https://rose1.ntu.edu.sg/dataset/actionRecognition","GATED: EULA; dossier vide; retire du catalogue-40"),
 ("auxdata","uci_parkinson_voix","UCI Parkinson's (voix)","auxdata/uci_parkinson_voix","non","auxi","direct","","fine-tuning seulement; 195 phonations"),
 ("auxdata","kaggle_spiral","UCI Spiral / Kaggle NIATS","auxdata/kaggle_spiral","non","auxi","direct","","dessins spirale/onde"),
 ("auxdata","nqmitcsxpd","neuroQWERTY MIT-CSXPD","auxdata/nqmitcsxpd","OUI","auxi","physionet","","frappe clavier"),
 ("auxdata","tappy_keystroke","Tappy Keystroke","auxdata/tappy_keystroke","non","auxi","physionet","","PhysioNet tappy 1.0.0"),
]


def scan(sub):
    def sf(p):
        if not os.path.isdir(p):
            return 0, 0
        tot = n = 0
        for dp, _, fs in os.walk(p):
            for f in fs:
                if f.startswith("._") or f == ".DS_Store":
                    continue
                try:
                    tot += os.path.getsize(os.path.join(dp, f)); n += 1
                except OSError:
                    pass
        return tot, n
    rb, rn = sf(os.path.join(ROOT, sub, "raw"))
    pb, pn = sf(os.path.join(ROOT, sub, "processed"))
    return rb, rn, pb, pn


def human(b):
    for u in ["o", "Ko", "Mo", "Go"]:
        if b < 1024:
            return f"{b:.0f}{u}"
        b /= 1024
    return f"{b:.1f}To"


ACCESS_TO_ACCES = {
    "direct_download": "direct", "free download": "direct", "direct": "direct",
    "account": "form", "application": "request", "request": "request",
    "form": "form", "DUA": "request",
}


def from_index(repo="."):
    """Rows for datasets that live in docs/datasets_index.csv (rendered by
    gen_datacards.py from its DATA table, the single source of truth) but are
    not in the hand-written CAT list above. Added 2026-08-22: CAT had drifted
    43 datasets behind the v2 expansion, so every new set was silently missing
    from _catalogue.csv and therefore from the taxonomy matrix. New datasets now
    flow in on their own; CAT stays authoritative for anything it already names."""
    idx = os.path.join(repo, "docs", "datasets_index.csv")
    if not os.path.exists(idx):
        return []
    known = {c[1].lower() for c in CAT}
    out = []
    with open(idx, newline="") as f:
        for r in csv.DictReader(f):
            jeu = (r.get("id") or "").strip()
            if not jeu or jeu.lower() in known:
                continue
            path = (r.get("path") or "").strip()
            sub = path[len("datasets/"):] if path.startswith("datasets/") else path
            if not sub:
                continue
            acc = (r.get("access") or "").strip()
            acces = ACCESS_TO_ACCES.get(acc, "")
            if not acces:
                low = acc.lower()
                acces = ("request" if ("applic" in low or "dua" in low)
                         else "form" if "account" in low
                         else "direct" if "download" in low or "public" in low
                         else "request")
            out.append(((r.get("family") or "").strip(), jeu,
                        (r.get("title") or jeu).strip(), sub, "OUI", "oui",
                        acces, (r.get("link") or "").strip(),
                        "auto from docs/datasets_index.csv; "
                        + (r.get("status") or "").strip()[:110]))
    return out


def main():
    rows = []
    for mod, jeu, nom, sub, nouveau, fm, acces, lien, note in list(CAT) + from_index():
        rb, rn, pb, pn = scan(sub)
        statut = "traite" if pn > 0 else ("telecharge_brut" if rn > 0 else "a_telecharger")
        rows.append([mod, jeu, nom, sub, nouveau, fm, acces, statut,
                     human(rb), rn, human(pb), pn, lien, note])
    out = os.path.join(ROOT, "_catalogue.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["modalite", "jeu", "nom", "dossier", "nouveau", "alimente_fm",
                    "acces", "statut", "taille_raw", "n_raw", "taille_proc",
                    "n_proc", "lien_manuel", "notes"])
        w.writerows(rows)

    from collections import Counter
    c = Counter(r[7] for r in rows)
    print(f"{out}: {len(rows)} jeux -> {dict(c)}")
    print("\nGATED (acces manuel requis):")
    for r in rows:
        if r[6] in ("synapse", "ieee", "form", "request") and r[7] == "a_telecharger":
            print(f"  [{r[0]}] {r[2]}  ({r[6]})  {r[12]}")


if __name__ == "__main__":
    main()
