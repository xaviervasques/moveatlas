# CARE-PD (9-cohort PD gait, canonicalized SMPL)

- dataset: care_pd
- family: pose  (physical path: datasets/pose/care_pd)
- MoveAtlas cells: B2, B3; M1
- population: 362 subjects, 9 cohorts, 8 sites; UPDRS_GAIT labels on 4 cohorts (3DGait, BMCLab, PD-GaM, T-SDU-PD)
- n_subjects: 362
- signal: 3D positions derived from canonicalized SMPL (24 joints), 25-150 fps per cohort, ~3.72 M frames, 8,476 walks
- license: CC BY-NC-ND 4.0, SETTLED 2026-08-25 by the official NeurIPS 2025 site (neurips2025.care-pd.ca): 'Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 ... may be used for non-commercial research and educational purposes with appropriate citation but may not be modified or redistributed in altered form'. The old tag-vs-README ambiguity (pinned 2026-08-22) is resolved in the tag's favour. Per-cohort originals differ (BMCLab and DNE are CC BY 4.0); the GitHub MIT covers the CODE only ; redistribution: NO: ND. Harmonized/derived tensors must never be redistributed, and training that publishes a model is a derivative-work risk: EVAL ONLY
- access: free download (moved 2026-08-25: HuggingFace vida-adl/CARE-PD is public again, plus UofT Borealis doi:10.5683/SP3/TWIKMK; the old TaatiTeam slug 404s, which looked like a lockdown and was a relocation)
- status (2026-08-22): INGESTED v1: 8,476 canonical records; ND ruling 2026-08-25: records stay internal, eval-only, excluded from every public release and from training that publishes weights
- link: https://neurips2025.care-pd.ca/index.html
- ingestion: extract_care_pd.py (SMPL -> 24-joint positions, conda env smpl) then build_canonical.py (smpl_carepd mapping). Verification: floor y~0, head y~1.5 m, UPDRS_GAIT distribution conform (3DGait {0:24,1:42,2:14,3:10})
- notes: the licence email is no longer needed (the NeurIPS site answered it); citations: NeurIPS 2025 paper arXiv 2510.04312, dataset DOI 10.5683/SP3/TWIKMK (DataCite-verified). Corresponding authors Adeli and Taati remain the contact for any data-contribution inquiry
