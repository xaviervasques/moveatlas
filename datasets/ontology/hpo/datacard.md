# Human Phenotype Ontology (movement pivot)

- dataset: hpo
- family: ontology  (physical path: datasets/ontology/hpo)
- MoveAtlas cells: semantic pivot for stage C; M9, M12
- population: knowledge base: 19,034 active terms; movement subtree HP:0100022 = 197 terms, 68 inside the 13 MoveAtlas anchor subtrees (verified this session)
- n_subjects: n/a
- signal: hp.obo (10 MB) + genes_to_phenotype.txt (19.7 MB) + phenotype.hpoa.gz + phenotype_to_genes.txt.gz; release hp/2025-01-16
- license: HPO free-use with attribution (widely mirrored) ; redistribution: yes
- access: obtained VIA PyPI (pyhpo 4.0.0 bundles the release) because GitHub release assets are outside the session egress; refresh lane in fetch_p2_lot.py
- status (2026-08-22): DOWNLOADED 2026-08-22 (this session) + verified: all 13 taxonomy anchor codes resolve to the expected names (A1 Tremor .. B5 Freezing of gait)
- link: https://hpo.jax.org/
- ingestion: build_hpo_movement_map.py -> docs/hpo_movement_terms.csv (id, name, depth, parents, MoveAtlas cells)
- notes: the label vocabulary of rule R2 / stage C weak alignment
