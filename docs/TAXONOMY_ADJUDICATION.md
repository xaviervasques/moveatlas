# Taxonomy adjudication sheet: registry vs taxonomy_map (2026-09-01)

The registry (`docs/datasets_index.csv`, served by `moveatlas.list_datasets()`)
and `docs/taxonomy_map.csv` disagree on the clinical cells of 20
datasets. The registry is the operational truth (the site and package
read it); the map carries some clinical distinctions the registry
lost. This sheet gives the evidence and a recommendation per dataset so
the owner can rule quickly. After ruling: apply to the REGISTRY, mark
`docs/taxonomy_map.csv` as superseded (or regenerate it from the
registry), and add a consistency lint to `release_lint.py` so two
truths can never drift again.

Recommendation legend: UNION = keep both sources' cells; REGISTRY /
MAP = one side is right; OWNER = genuine clinical call.

| # | Dataset | Map | Registry | Recommendation | Rationale |
|---|---------|-----|----------|----------------|-----------|
| 1 | li_taati | B2, E6 | A4, A7, B2, E6 | **REGISTRY** | L-DOPA dyskinesias are choreiform (A7) with dystonic features (A4); the registry entry is the later refinement. |
| 2 | care_pd | B3 | B2 | **UNION B2+B3** | PD gait carries both slowness (B2) and reduced amplitude (B3); the B2-vs-B3 split below repeats across all gait sets and deserves ONE standing rule. |
| 3 | visionmd | B2 | (none) | **REGISTRY** | Ruled a TOOL, excluded from the catalogue; remove it from the map. |
| 4 | toronto_neuroface | D3 | A4, D3 | **OWNER** | Orofacial impairment in ALS/stroke is weakness, not dystonia; A4 reads as an over-reach ("A4 orofacial-adjacent"). Suggest dropping A4 unless the OFA tasks include dystonic patients. |
| 5 | modys_video | A4, A6, A7, D3 | A4, A7 | **UNION (add A6, D3)** | Dyskinetic CP is choreoATHETOSIS; the paper's DIS scale scores athetosis explicitly. HIGH STAKES: this is the only OPEN harmonized dataset that would cover A6, which is otherwise CODY-only. D3 covers the CP spasticity component. |
| 6 | koa_pd_nm | B2, B3, C1, E4 | B2, C1, E4 | **UNION (add B3)** | Same B2/B3 rule as #2. |
| 7 | gavd | B3, D3 | (none) | **REGISTRY** | Ruled a label/reference source, not a signal corpus; remove from the map. |
| 8 | weargait_pd | B2, B3, C1 | B2, B3 | **UNION (add C1)** | The cohort has healthy controls (HC subject ids in the manifests). |
| 9 | pads | A1, B2, D3 | A1, B2 | **OWNER** | The differential cohorts include multiple sclerosis; D3 (pyramidal) is the nearest cell but MS is not purely pyramidal. Suggest adding D3 with a "differential cohorts" note, or leaving as-is deliberately. |
| 10 | pd_biostamprc21 | B2, B3 | B2 | **UNION (add B3)** | Same B2/B3 rule. |
| 11 | physionet_gaitpdb | B2, B3 | B2 | **UNION (add B3)** | Same B2/B3 rule. |
| 12 | gaitndd | A7, C1, D3 | A7, B2, D2 | **UNION with FIX: A7, B2, C1, D3; DROP D2** | ALS is a motor-neuron/pyramidal disease (D3), not ataxia (D2): the registry's D2 looks like an error ("D2-adjacent"). The cohort has 16 healthy controls (C1) and a PD arm (B2). |
| 13 | clinical_gait_multipatho | B3, D3, D4, E4 | B2, D3, D4, E4 | **UNION B2+B3** | Same B2/B3 rule. |
| 14 | imu_inthewild_iprognosis | A1 | A1, B2 | **REGISTRY** | i-PROGNOSIS captures general PD motor signs on the phone, not tremor alone; later refinement. |
| 15 | monipar | A1, B2 | A1 | **UNION (add B2)** | Smartwatch PD monitoring measures more than tremor; the map kept the broader intent. |
| 16 | gaitdb | B3, C3 | B2, C3 | **UNION B2+B3** | Same B2/B3 rule (aging + disease cohort). |
| 17 | uci_parkinson_voix | B2 | (none) | **ADD "B2 proxy"** | Hypokinetic dysarthria is a bradykinesia proxy; mirror the kaggle_spiral "A1 proxy" pattern so proxies stay distinguishable from measured movement. |
| 18 | kaggle_spiral | A1, B2 | A1 | **UNION (add "B2 proxy")** | Spiral drawing degrades with both tremor and bradykinesia. |
| 19 | pd_walking_eeg_ds007526 | B2 | B2, B5 | **REGISTRY** | The walking protocol makes it FOG-adjacent (B5); later refinement. |
| 20 | capture24 | C1, C3 | C1 | **UNION (add C3)** | 151 subjects across a wide age range; the aging axis applies. |

| 21 | accel_fluctuations | B4 | **ABSENT from the registry** | **ADD as barrier** | The MJFF Levodopa Response Study lives in the map (B4, access refused/ACT) but never entered `datasets_index.csv`. It is the only B4 candidate in either source: adding it as a documented barrier makes the B4 row honest ("1 catalogued, 0 open") instead of empty. |

## The standing B2/B3 rule (decides #2, 6, 10, 11, 13, 16)

Proposal: a PD/parkinsonian GAIT dataset gets **B2 AND B3** (slowness
and amplitude are both expressed in gait), while task-specific sets
keep the cell their task isolates (finger tapping -> B2; amplitude
protocols -> B3). One sentence in the registry header documents the
rule; then the six gait cases above resolve mechanically.

## Consequences on the published tables

The modality-by-symptom matrix, taxonomy small multiples and per-cell
counts on the site all read the registry and regenerate at build time;
no other edits needed after the ruling. B3's count would go from 2 to
~8, A6 would gain its first open dataset, D2 would lose a wrong member.

## After the ruling (mechanical, any session can do it)

1. Edit `docs/datasets_index.csv` cells per the rulings.
2. Regenerate: gen_datacards -> build_citations -> gen_dataset_pages +
   gen_figures -> sphinx build.
3. Retire or regenerate `docs/taxonomy_map.csv` from the registry.
4. Add the registry-vs-map consistency check to `release_lint.py`
   (or delete the map so there is nothing to drift).
