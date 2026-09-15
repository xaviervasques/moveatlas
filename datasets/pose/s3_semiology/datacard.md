# Seizure-Semiology-Suite (S3, UCLA)

- dataset: s3_semiology
- family: pose  (physical path: datasets/pose/s3_semiology)
- MoveAtlas cells: D1; M1 (video), labels
- population: 116 adult epilepsy patients, 438 seizure videos, >35,000 dense labels on 20 ILAE semiology features
- n_subjects: 116
- signal: seizure videos (not yet released) + benchmark/annotation artefacts in the authors' GitHub repo
- license: repo has NO LICENSE FILE (checked 2026-08-22) = all rights reserved by default; videos under a DUA that is not open yet ; redistribution: no (neither part)
- access: application (DUA) for videos; repo artefacts unlicensed
- status (2026-08-22): REPO LOCATED 2026-08-22: github.com/LinaZhangUCLA/SeizureSemiologySuite (ICML 2026 spotlight, pushed 2026-05-26, ~57 MB, 801 csv + 36 json + 7 jsonl). It holds the benchmark/fine-tuning artefacts and split tables, NOT the videos; the paper's Dataset link is still a placeholder. NOTHING FETCHED INTO THIS REPO: no license means no redistribution right, and the DUA is still in the human queue. DOCUMENTED BARRIER (owner, 2026-08-28): the publication focuses on genuinely open data; the DUA route is not pursued. Evidence recorded 2026-08-28: the videos NEVER leave UCLA; authorized users analyze inside a UCLA-hosted secure enclave after an institutional DUA plus project IRB approval, so local training was off the table anyway; the repo's annotation CSVs stay look-don't-mirror (no licence file)
- link: https://arxiv.org/abs/2605.21852
- notes: exactly the D1 target: movement during seizures with ILAE feature labels. 438 videos / 116 adults (300 ES, 138 NES), ages 18-64, tertiary EMU 2019-2023, IRB-approved and de-identified; 20 ILAE features each with presence, MM:SS boundaries and free-text justification. Labels: eval only (R1), never pretraining
