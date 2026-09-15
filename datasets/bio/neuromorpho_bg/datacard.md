# NeuroMorpho.Org basal-ganglia neuron morphologies

- dataset: neuromorpho_bg
- family: bio  (physical path: datasets/bio/neuromorpho_bg)
- MoveAtlas cells: A7 (HD models), B1-B3 (PD models), M10 (cellular morphology)
- population: 7,842 striatal reconstructions; DISEASE-MODEL CONTENT measured from the metadata (processed/condition_breakdown.csv, analyze_neuromorpho_conditions.py, 2026-09-01): Huntington 823 (675 Q140 labeled Huntington's Disease + 148 zQ175/Q175) -> A7; Parkinson models 248 (139 alpha-synuclein BAC rat, 71 LRRK2, 38 6-OHDA) -> B lane; stroke MCAO 52; dopaminergic pharmacology ~330 (cocaine, nicotine+SCH23390, D2R-overexpression) -> the intervention axis; 124 HUMAN neurons (all controls: no human patient morphology exists here); ~6,640 healthy/control baseline. The symptom link is via the animal disease model, not measured movement
- n_subjects: region-filtered subset
- signal: .swc reconstructions via the public API (scraping forbidden, API allowed)
- license: CC BY 4.0 (verified on useterm.jsp 2026-09-01) ; redistribution: yes
- access: NeuroMorpho API bulk download
- status (2026-08-22): DOWNLOADED 2026-09-01 (owner GO): metadata for 7,842 striatal neurons + 7,567 CNG .swc reconstructions (372 MB; 275 neurons have no CNG file at the archive, counted as errors not retried). Metadata ALSO fetched for ventral striatum / motor cortex / cerebellum / basal forebrain (--meta-only): the region queries overlap heavily and the disease-model content was already inside the striatal pull. Condition breakdown measured: processed/condition_breakdown.csv (HD 823 -> A7 analog, PD models 248, pharmacology ~330, 124 human all controls). Region vocabulary has no pallidus/nigra/STN tokens (casebook adjacent phenomenon)
- link: https://neuromorpho.org
