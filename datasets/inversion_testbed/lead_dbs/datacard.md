# Data card : Lead-DBS atlases + STN sweet spots (inversion testbed, anatomical prior)

- Source : Lead-DBS (https://www.lead-dbs.org), Horn & Kuehn and collaborators.
- Key resource : DISTAL atlas (Ewert et al. 2018) - histology + structural-connectivity
  based subcortical atlas coregistered to ICBM 2009b NLIN ASYM MNI space, with the STN
  subdivided into sensorimotor / associative / limbic subregions.
- DBS sweet spots : Dembek et al. 2019, Horn et al. - MNI-space maps of stimulation sites
  associated with best motor outcome in STN-DBS for PD.
- Licence : freely available for research through Lead-DBS (atlases ship with the toolbox;
  see lead-dbs.org atlas pages). Individual atlas licences per the Lead-DBS documentation.

## What this is (and is NOT)

This is an ANATOMICAL PRIOR, not a paired motor+electrophysiology recording. It provides,
in MNI space, which STN functional subregion a given DBS contact or LFP bipolar pair sits
in, and where the therapeutic sweet spot lies. There is no movement time series here.

## Role in the inversion testbed

Context for interpreting the two functional datasets:
- Place each STN-LFP channel (Merk, Oxford) into the sensorimotor vs associative/limbic
  subregion, when electrode coordinates are available (Merk ships electrodes.tsv +
  coordsystem.json + Lead-DBS ea_ui .mat).
- Ask whether the inverse mapping (movement -> LFP signature) is stronger for contacts in
  the sensorimotor STN / near the sweet spot. A neuroanatomical covariate for the probe,
  not a training signal.

## Status

Reference resource. Download the DISTAL atlas + sweet-spot maps from lead-dbs.org when the
probe needs contact localisation; not fetched automatically (it is a toolbox resource, not
a per-subject dataset). No canonical contract - out of pretraining by design.
