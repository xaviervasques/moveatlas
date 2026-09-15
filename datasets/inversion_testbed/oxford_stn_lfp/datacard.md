# Data card : Oxford STN-LFP grip force (inversion testbed, secondary)

- Paper : Tan et al. 2016, "Decoding gripping force based on local field potentials
  recorded from subthalamic nucleus in humans", eLife 2016;5:e19089.
- Group : MRC Brain Network Dynamics Unit / Nuffield Dept of Clinical Neurosciences,
  University of Oxford.
- Corresponding author (for raw data requests) : huiling.tan@ndcn.ox.ac.uk

## Signals

- MOTOR : grip force on a dynamometer, self-selected effort levels (0-10 scale), visual
  cues, ~31 +/- 2 grips per hand.
- ELECTROPHYSIOLOGY : subthalamic LFP (also EMG), same subject/time.
- Sampling : LFP, EMG, force initially at 2048 Hz.
- Cohort : 11 idiopathic PD patients (21 STN recorded) + a 10-patient independent
  validation cohort.
- Finding (original direction) : STN gamma (55-90 Hz) and beta (13-30 Hz) most informative
  about grip force; a first-order dynamic linear model decodes the force time course from
  those LFP features. Our probe runs this INVERSE (force -> LFP features).

## Availability

- PUBLIC : the eLife article ships figure source data (elife-19089-fig*-data*.mat/.xlsx)
  with the processed grip-force and LFP-feature relationships behind each figure. These
  are downloadable from the article and are enough for a first inverse-direction check on
  the published features.
- RAW (full per-trial LFP + force time series) : not deposited in an open repository as of
  this writing; request from the corresponding author. The MRC BNDU operates a data-
  sharing platform (data.mrc.ox.ac.uk) - check there first.

## Role / scope

Second independent cohort for the inversion probe (`eval/inversion_probe.md`), at a
different sampling rate (2048 Hz) and a self-paced task, so it tests generalisation of the
inverse mapping beyond the Merk Go/No-Go paradigm. Same scope discipline: LFP is a probe
TARGET, never pretraining.

## Status (2026-07-16)

Figure source data : URLs located (elife-19089-fig1..7-data1-v2.mat/.xlsx) but the eLife
download CDN returns HTTP 406 to automated clients (bot protection). Download them by hand
from https://elifesciences.org/articles/19089/figures (owner, a few small files).
Raw (full LFP + force time series) : request from huiling.tan@ndcn.ox.ac.uk / check the
MRC BNDU data-sharing platform (data.mrc.ox.ac.uk). Not an automated fetch.
