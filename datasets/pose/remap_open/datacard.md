# REMAP open subset (Bristol)

- dataset: remap_open
- family: pose  (physical path: datasets/pose/remap_open)
- MoveAtlas cells: B2, B3; M1
- population: 12 PD (mean 61.25 y) + 12 controls (mean 59.25 y); home free-living + clinical assessment; PD on/off labels
- n_subjects: 24
- signal: coarsened 2D skeletons (sit-to-stand + turns) and coarsened 3D (turns)
- license: CC BY 4.0 (warranty disclaimer) ; redistribution: yes
- access: direct_download (single 351.4 MiB zip; fetch_p2_lot.py --only remap_open)
- status (2026-08-22): DOWNLOADED AND INGESTED 2026-08-25 (Paris session): 189.4 MB zip (CRC clean, 19,711 entries), then 3,901 canonical pose records / 24 subjects, exactly the published cohort (12 PD + 12 controls), 0 refusals. Turning: 1,749 episodes as H36M-17 (identification evidence in configs/canonical_skeleton.yaml), both the coarsened 2D and the source-lifted 3D (lift_provenance=videopose3d_by_source, pool config decides use). Sit-to-stand: 403 episodes as OpenPose BODY_25 with per-file frame+timestamp columns, fps measured from the data's own clock (30.0). PD/control rides as group attribute + eval-only label. Controlled sibling (full-res + 30 Hz wrist accel) stays application-gated (DOI 10.5523/bris.2o94rzjooyzf42w850dqg0spfh)
- link: https://data.bris.ac.uk/data/dataset/21h9f9e30v9cl2fapjggz4q1x7
- citation: Sci Data 2023, doi 10.1038/s41597-023-02663-5
