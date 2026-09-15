# Hunt: EuroMov (Montpellier) open datasets - 2026-09-02

Owner prompt: EuroMov (EuroMov Digital Health in Motion, Univ.
Montpellier / IMT Mines Ales) publishes movement-and-health research;
their datasets are said to live scattered across Zenodo, GitHub and HAL.
Is there additional data for the corpus?

## Sweep (all queries run 2026-09-02)

1. **Zenodo** `q="EuroMov"`: 15 hits, dominated by preprints, theory
   papers and software. ONE movement-disorders data item:
   - "Latent-Space Interpretation of Wearable Gait Biomarkers Following
     a Sophrology-Based Body-Awareness Intervention in Parkinsonian
     Gait" (10.5281/zenodo.20314642, CC BY 4.0, 2026-05-20): plantar
     pressure + gait metrics, **a single participant** (n=1), 185 KB.
     Below any useful threshold for the corpus. NO-GO recommended.
   Two more movement-adjacent items are methodology only (2D-DFA in
   obstetrics; VR social synchronization).
2. **HAL** `structAcronym_s:EuroMov AND docType_s:DATASET`: **0**
   datasets under the structure.
3. **Recherche Data Gouv** (entrepot.recherche.data.gouv.fr): API and
   site both serving an "En maintenance" page today; RETRY later, this
   is the one channel not actually swept.
4. **GitHub** `q=euromov`: 12 repos; the three EuroMov-affiliated ones
   with a data flavor are pipelines without hosted data (AMSTROM
   EMG/torque/NIRS preprocessing, locomotor-resilience RAS internship
   pipeline, REBA ergonomic CV). No downloadable movement data.

## Verdict

Under the lab's own name the open-data yield is essentially nil: the
lab publishes research, not lab-branded deposits. Their PD/gait output
(rhythmic auditory stimulation work and similar) reaches repositories
under individual authors' names and journal supplements, which the
topic-level hunts already sweep. Two follow-ups if the owner wants
more: (a) retry Recherche Data Gouv when it is back up; (b) a
researcher-name pass (Dalla Bella, Bardy, Geny, Ramdani, Blain) - low
expected yield since the topic hunts covered PD gait broadly.

No GO candidates produced by this sweep.
