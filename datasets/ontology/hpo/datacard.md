# Human Phenotype Ontology (movement pivot)

- dataset: hpo
- family: ontology  (physical path: datasets/ontology/hpo)
- MoveAtlas cells: semantic pivot for stage C; M9, M12
- population: knowledge base: 19,034 active terms; movement subtree HP:0100022 = 197 terms, 68 inside the 13 MoveAtlas anchor subtrees (verified this session)
- n_subjects: n/a
- signal: hp.obo (10 MB) + genes_to_phenotype.txt (19.7 MB) + phenotype.hpoa.gz + phenotype_to_genes.txt.gz; release hp/2025-01-16
- license: HPO free-use with attribution (hpo.jax.org/license, read 2026-09-16: cite the HPO, show the file version when displayed, do not alter the content) ; redistribution: yes
- access: obtained VIA PyPI (pyhpo 4.0.0 bundles the release) because GitHub release assets are outside the session egress; refresh lane in fetch_p2_lot.py
- status (2026-08-22): DOWNLOADED 2026-08-22 (this session) + verified: all 13 taxonomy anchor codes resolve to the expected names (A1 Tremor .. B5 Freezing of gait)
- link: https://hpo.jax.org/
- citation: This service uses the Human Phenotype Ontology (release 2025-01-16). Find out more at https://hpo.jax.org/ ; cite Gargano et al., Nucleic Acids Research 2024, doi 10.1093/nar/gkad1005
- ingestion: build_hpo_movement_map.py -> docs/hpo_movement_terms.csv (id, name, depth, parents, MoveAtlas cells, HPO release); the HPO files are redistributed unmodified and the subset keeps ids, names and parents as released
- notes: the label vocabulary of rule R2 / stage C weak alignment
