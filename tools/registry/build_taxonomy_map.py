# -*- coding: utf-8 -*-
"""Projette le catalogue disque (datasets/_catalogue.csv) sur la taxonomie MoveAtlas v2.

Additif : ne modifie aucun outil existant (build_catalogue.py, build_access_log.py,
paper/build_tables.py restent inchanges). Aucun nombre en dur : tout vient du
catalogue et de docs/taxonomy_map.csv.

Entrees :
  datasets/_catalogue.csv   (regenere par build_catalogue.py ; cle = colonne 'jeu')
  docs/taxonomy_map.csv     (mapping jeu -> cellules taxonomiques ; maintenu a la main)
Sorties :
  paper/matrix_taxonomy.csv (une ligne par cellule : effectifs par statut + liste des jeux)
  stdout : resume par classe + avertissements (jeu non mappe, cellule inconnue)

Usage :
  python build_taxonomy_map.py [--repo <racine du repo>]

Reference des cellules : MoveAtlas_Matrice_couverture_v2.xlsx, feuille Taxonomie
(classes A1-A8, B1-B5, C1-C3, D1-D7, E1-E7 ; modalites M1-M12).
"""
import argparse
import csv
import os
import sys
from collections import defaultdict

CELLS_VALID = (
    [f"A{i}" for i in range(1, 9)]
    + [f"B{i}" for i in range(1, 6)]
    + [f"C{i}" for i in range(1, 4)]
    + [f"D{i}" for i in range(1, 8)]
    + [f"E{i}" for i in range(1, 8)]
)
MODS_VALID = [f"M{i}" for i in range(1, 13)]
CLASS_LABEL = {
    "A": "Hyperkinetique",
    "B": "Hypokinetique",
    "C": "Normal (conditionne a l'age)",
    "D": "Comorbidites neurologiques",
    "E": "Comorbidites systemiques",
}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO", "."))
    args = ap.parse_args()

    cat_path = os.path.join(args.repo, "datasets", "_catalogue.csv")
    map_path = os.path.join(args.repo, "docs", "taxonomy_map.csv")
    out_path = os.path.join(args.repo, "paper", "matrix_taxonomy.csv")

    catalogue = {r["jeu"]: r for r in read_csv(cat_path)}
    mapping = {r["jeu"]: r for r in read_csv(map_path)}

    warnings = []
    infos = []
    for jeu in catalogue:
        if jeu not in mapping:
            warnings.append(f"jeu non mappe dans taxonomy_map.csv : {jeu}")
    for jeu in mapping:
        if jeu not in catalogue:
            infos.append(f"pre-enregistre, pas encore sur disque : {jeu}")

    per_cell = defaultdict(lambda: {"jeux": [], "statuts": defaultdict(int), "mods": set()})
    for jeu, m in mapping.items():
        if jeu not in catalogue:
            continue
        statut = catalogue[jeu].get("statut", "?")
        cells = [c.strip() for c in m.get("cellules", "").split(";") if c.strip()]
        mods = [c.strip() for c in m.get("modalites_m", "").split(";") if c.strip()]
        for c in cells:
            if c not in CELLS_VALID:
                warnings.append(f"cellule inconnue '{c}' pour {jeu}")
                continue
            per_cell[c]["jeux"].append(jeu)
            per_cell[c]["statuts"][statut] += 1
            per_cell[c]["mods"].update(mods)
        for md in mods:
            if md not in MODS_VALID:
                warnings.append(f"modalite inconnue '{md}' pour {jeu}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    statut_keys = sorted({s for d in per_cell.values() for s in d["statuts"]})
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cellule", "n_jeux"] + [f"n_{s}" for s in statut_keys] + ["modalites", "jeux"])
        for cell in CELLS_VALID:
            d = per_cell.get(cell)
            if d is None:
                w.writerow([cell, 0] + [0] * len(statut_keys) + ["", ""])
            else:
                w.writerow(
                    [cell, len(d["jeux"])]
                    + [d["statuts"].get(s, 0) for s in statut_keys]
                    + [";".join(sorted(d["mods"])), ";".join(sorted(d["jeux"]))]
                )

    print(f"ecrit : {out_path}")
    print()
    print("Couverture par classe (jeux du catalogue disque uniquement ;")
    print("les candidats non telecharges vivent dans MoveAtlas_Matrice_couverture_v2.xlsx) :")
    for klass, label in CLASS_LABEL.items():
        cells = [c for c in CELLS_VALID if c.startswith(klass)]
        covered = [c for c in cells if per_cell.get(c)]
        empty = [c for c in cells if not per_cell.get(c)]
        print(f"  {klass} {label} : {len(covered)}/{len(cells)} cellules servies ; vides : {', '.join(empty) if empty else 'aucune'}")
    if infos:
        print()
        print("Pre-enregistres (datacard posee, donnee attendue ; hors comptage ci-dessus) :")
        for imsg in infos:
            print("  -", imsg)
    if warnings:
        print()
        print("AVERTISSEMENTS :")
        for wmsg in warnings:
            print("  -", wmsg)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
