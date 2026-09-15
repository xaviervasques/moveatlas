# Access-barrier case studies for the resource paper

Written 2026-08-25 at the owner's direction: rather than resolving every
barrier before publication, the paper REPORTS them as findings. Each case
below is documented with its evidence trail so the paper's barriers section
can cite specifics, not anecdotes. Machine-readable companions:
paper/table_barriers.csv, docs/license_matrix.csv, datasets/_access_log.csv.

## Case 1: published but never deposited (beijing_sleep_lfp)

The 121-patient basal-ganglia sleep-LFP cohort exists in the literature (npj
Digital Medicine 2024, 10.1038/s41746-024-01115-7) but the recordings were
never deposited in any repository. Access = "upon reasonable request" to the
authors, i.e. an email, a wait, and usually a data use agreement. This is the
DOMINANT pattern for invasive electrophysiology: of the M7 (LFP/ECoG) sources
identified, only two are openly downloadable (ds004998, oxford_dystonia_lfp)
and both are small. Request drafted (docs/DRAFT_EMAILS_2026-08-23.md), not
yet sent at write time.

Paper point: for whole classes of clinically decisive signal, the bottleneck
is not discovery but the absence of any deposit; "available on request" is an
access route whose latency and success rate are unmeasurable in advance (our
access log records request dates prospectively).

OWNER DECISION 2026-08-25: the request will NOT be sent. The project reports
the barrier as a finding instead of spending its calendar on author
correspondence; the drafted letter stays in DRAFT_EMAILS_2026-08-23.md as an
artifact of what the route would cost. Same ruling for the ds007526 scale
question (case 3): the 277 records stay flagged AMPLITUDE IMPLAUSIBLE and
excluded, and the paper reports declared-unit-vs-values disagreement as a
reproducible hazard of open EEG deposits.

## Case 2: data in hand, licence self-contradictory (care_pd)

CARE-PD is downloaded and ingested (8.5k canonical records). The blocker is
purely legal: the HuggingFace dataset card's YAML tag says `cc-by-nc-nd-4.0`
while the README body grants "CC BY-NC 4.0" twice, including in the warranty
clause. Both statements describe the same object and disagree on exactly the
clause (NoDerivatives) that decides whether training and harmonized
redistribution are permitted. Since 2026-08-22 the repo is additionally
gated (HTTP 401 without a logged-in request), so the contradiction can only
be checked from a HuggingFace account. Clarification email drafted.

A third licence object was checked 2026-08-25: the TaatiTeam/CARE-PD GitHub
repository ships an MIT LICENSE.txt, which covers the CODE only ("the
Software"). One project therefore carries three licence statements across
three objects (code MIT, data tag CC BY-NC-ND, data README CC BY-NC), and
only a written answer from the maintainers settles which governs the data.

Timeline of the repo's visibility, each step observed first-hand: OPEN in
July (we downloaded and ingested then), GATED on 2026-08-22 (HTTP 401 to
anonymous requests), and by 2026-08-25 the old slug 404s even to a logged-in
account. What LOOKED like a lockdown was a RELOCATION: the owner found the
official NeurIPS 2025 site (neurips2025.care-pd.ca), which points at a new
public HuggingFace slug (vida-adl/CARE-PD, HTTP 200) and a UofT Borealis
deposit (doi:10.5683/SP3/TWIKMK, DataCite-registered).

RESOLUTION (2026-08-25): the official site states the licence unambiguously,
CC BY-NC-ND 4.0, "may not be modified or redistributed in altered form". The
two-year-old tag-vs-README ambiguity is settled in the tag's favour, without
an email: the answer was published, just not where we were looking. Ruling
applied: CARE-PD stays in the corpus for EVALUATION ONLY, its harmonized
records are excluded from every public release. Paper lessons: (a) a dataset
that moves looks identical to a dataset that locks down, and only finding its
new home tells them apart; (b) licence ambiguities sometimes resolve
themselves in later releases, so re-checking upstream before writing the
clarification email is worth five minutes.

Related pattern, resolved this session and worth its own sentence in the
paper: a Scientific Data ARTICLE licence (often CC BY-NC-ND) is routinely
mistaken for the licence of the DATASET it describes; for cervical_motion and
clinical_gait_2025 the figshare deposits are CC BY 4.0 while the articles are
ND. Reading the article's rights footer as the data licence mislabels the
data. Two of our own three "licence blockers" dissolved this way.

## Case 3: data public, values contradict their declaration (ds007526)

ds007526 (PD walking EEG, OpenNeuro, CC0) is public, downloaded, ingested:
277 records. Every record's stored values sit ~1000x above scalp-EEG
amplitude under the dataset's own declared unit (channels.tsv says uV; mne
applies the standard EEGLAB uV convention; stored p99 ~2.7e5). Per the corpus
rule (never rescale on a guess) all 277 records carry an AMPLITUDE
IMPLAUSIBLE flag and are unusable until the authors answer. Question drafted.

Paper point: open licences and tidy BIDS layouts do not guarantee usable
data; unit declarations must be checked against the values, and a corpus
needs an explicit policy for the disagreements (ours: flag, never repair
silently, ask the source).

## Case 4: open licence, closed format (gait120)

Downloaded whole (15.4 GB, every published md5 verified) under CC BY 4.0, yet
the sEMG payloads cannot be opened outside MATLAB: both RawData.mat and
ProcessedData.mat serialize MATLAB 'table' class objects (MCOS), an opaque
container scipy and every open .mat reader fail on. The licence permits
everything; the container permits nothing. Ingestion of the EMG waits on a
MATLAB/Octave export step or an MCOS parser; the OpenSim .mot joint angles
in the same deposit are plain text and readable. Paper point: FAIR's
"interoperable" is a property of the FILE FORMAT, not the licence, and a
data descriptor can pass review with its primary signal locked in a
single-vendor object.

RESOLUTION POSTSCRIPT (2026-08-28): the lock fell to community reverse
engineering, not to the vendor. The mat-io package (PyPI, MIT) decodes the
MCOS 'table' objects that scipy cannot, and one pass of
build_canonical_emg.py --only gait120 emitted 3,432 canonical EMG records
(raw 2000 Hz, 12 named right-leg muscles, unit volts) with zero refusals.
Two notes for the paper: (a) the barrier was real for as long as the format
went unparsed outside MATLAB, and a corpus builder without a fresh
third-party parser still hits it; (b) the 'Octave export' escape hatch this
case originally proposed was itself a dead end: Octave does not deserialize
MATLAB tables. The case stays in the paper as a resolved instance with a
measurable cost. Same-day corollary: the "10/10 zips complete" belief fell
too; the deposit really holds 12 zips (S001-S120) plus demographics and
anthropometrics, and completeness had to be re-established from the
figshare API file list, not from the download journal.

## Case 5: the transport arms race (figshare, resolved by changing CLIENT)

Fully documented in HANDOFF 9 section 4 and worth a compressed paragraph in
the paper: a VPN exit IP (403), a blacklisted self-identifying User-Agent
token (202 with, 302 without, same IP same file), TLS-fingerprint
discrimination (python/urllib permanently 202'd while curl passed, then curl
too), rate-limiting that punished every automated cadence tried (per-file
retries, round-robin sweeps, probe-then-burst), staging windows with 10 s
presigned-URL expiry that killed queued browser downloads, and finally
success: a REAL browser, one download in flight at a time, paced by
watching the filesystem. 56 files, every one md5-verified. The general
lesson: repository anti-bot defenses now discriminate on client identity at
several protocol layers at once, and the only universally accepted client is
the one a human uses.

RECURRENCE AND CLOSURE (rat7m, 2026-09-03/04): the same figshare 403
hit the rat7m video files on 2026-09-03 (scripted clients refused,
browser UA included, while the mocap article had served to the same
client days earlier). Per the case-5 doctrine no retry storm was run;
a single spaced probe ~14 h later returned HTTP 206 (normal S3
redirect) and the full 15.35 GB / 2028-file pull then completed with
zero errors and a sha256 journal. Second data point for the paper:
these blocks can be transient or rate-based, and one patient probe
beats any automated persistence.

## Adjacent phenomena observed the same week (one line each for the paper)

- **Access metadata ages fast, in BOTH directions.** Two gates listed in our
  July/August audit had silently disappeared by 2026-08-25: ninapro's
  registration wall (67 zips now serve directly) and MINI-RGBD's request
  form. Conversely CARE-PD gained a 401 gate after we mirrored it.
- **Repository-side throttling punishes bulk collection.** figshare answered
  403-then-202 to every request for three days; root cause turned out to be
  the collection machine's VPN exit IP, plus genuine per-file staging delays
  on large archives. Retry storms make it worse; one spaced probe rides it out.
- **Byte-identical duplicates hide under distinct names.** Two registry
  entries (fog_star_2026, clinical_gait_2025) turned out to be md5-identical
  to already-held deposits; without the checksum check each would have been
  double-counted, one with a phantom licence conflict.
- **The same subjects can straddle releases.** ltmm's release holds 79
  subject ids against the paper's 71 analysis cohort; seizeit2's BIDS release
  carries 883 seizure annotations against the paper's 886. Release and paper
  are different objects; counts must come from the data.

## Case 6: the open-data deserts, quantified (2026-09-01 sweep)

A licence-verified sweep across PhysioNet, OpenNeuro, Zenodo, figshare,
Dryad, OSF, IEEE DataPort, DANDI and Synapse, targeted at the weakest
cells of the taxonomy, confirmed that as of 2026-09-01 NO openly
downloadable data exists anywhere for five whole classes of movement
phenomenology: tics (every video/EMG corpus is institution-private; the
one Zenodo GTS EEG record is access-restricted), akinesia as its own
object (the space collapses into bradykinesia tapping sets), rigidity
as measured signal (KINARM/NeuroFlexor/Myoton studies uniformly say
"available on reasonable request"), kinematic Huntington chorea beyond
two small gait sets (Enroll-HD and every wearable HD study are gated),
and pharmacological-challenge kinematics (caffeine, alcohol: zero
deposits; the one open alcohol-dystonia object is a ratings table).

Paper point: scarcity is not anecdotal, it is enumerable. The
modality-by-symptom matrix makes the empty rows first-class results,
and the private CODY cohorts are the only data in existence for three
of the thirteen target cells.

## Case 7: published, benchmarked by a whole field, and licence-free
(goodwin_smm)

The canonical stereotypy accelerometry benchmark (Goodwin et al.,
UbiComp 2014) is anonymously clonable from a public repository and has
been reused by essentially every SMM detection paper since. It ships
NO data licence at all: the repository's LICENSE files all belong to
bundled third-party MATLAB libraries, and the linked instruction
document (archived at datasets/imu/goodwin_smm/
instruction_doc_20260901.txt) asks for citation only. A decade of
literature therefore rests on data nobody has the written right to
redistribute. MoveAtlas holds it INTERNAL-ONLY (mmasd precedent).

Bonus finding from the same acquisition, the declared-vs-measured
pattern of case 3 again but for calibration: the instruction document
declares the MITes sensors span +/-2g over 0-512 counts, while the
calm-window gravity method reads 64 counts/g on every file, i.e.
+/-4g; the declaration is wrong by exactly 2x. Wockets units had to be
established per file from their own gravity (per-device spread 91-110
counts/g), and 8 of 75 files were refused as undetermined rather than
guessed.

## Case 8: "open data" that turns out to be figures (lance_adams)

The only openly licensed myoclonus polygraphy found anywhere (Zenodo
7620808, CC BY 4.0) advertises EEG-EMG recordings with jerk-locked
back-averaging; the five files are four supplementary PDFs and a
patient video. The signal exists only as rendered figures. It stays
catalogued as case evidence, but the A2 cell's "open signal" count
remains zero.

Paper point: repository records inherit the vocabulary of signal
("EEG-EMG recording") for objects that are illustrations of signal;
open-data audits must open the files.

## Case 9: no human patient neuron morphology exists (neuromorpho_bg)

The 7,842 striatal reconstructions bulk-fetched from NeuroMorpho.Org
(CC BY 4.0, API route) were tagged against the taxonomy
(analyze_neuromorpho_conditions.py; processed/
condition_breakdown.csv): 823 neurons from Huntington knock-in models
(Q140, zQ175) speak to A7, 248 from Parkinson models (alpha-synuclein
BAC, LRRK2, 6-OHDA) to the B lane, ~330 from dopaminergic
pharmacology conditions to the intervention axis - and every one of
the 124 HUMAN neurons is a control. In the world's reference
morphology repository, the symptom-to-cell bridge exists ONLY through
animal disease models; human patient morphology for any movement
disorder is simply absent.

Paper point: the cellular substrate of the taxonomy is reachable
today through model organisms (morphology), human single units
(dystonia pallidal recordings, DBS surgeries) and human
transcriptomics (SNpc atlases) - three different species/scale
compromises that the atlas documents rather than blends.

## Adjacent phenomena, 2026-09-01 additions

- **Per-file endpoints and dataset endpoints disagree on anonymity.**
  Dryad answers 401 to anonymous per-file download links while the
  version-level zip endpoint of the same datasets serves anonymously;
  Zenodo served three files of a record then 504'd the rest for an
  hour. The transport layer, not the licence, decides the afternoon.
- **Repository search vocabularies under-report holdings.** The
  NeuroMorpho region query matched only the token "striatum"; pallidum,
  nigra and subthalamic queries return 404 despite such neurons
  existing under other region spellings. Coverage claims made through
  an API are lower bounds.
- **Two agent-reported "discoveries" were already ours.** WearGait-PD
  and the figshare turning deposit surfaced as misses in an automated
  sweep and were caught by id/DOI cross-checks in curation; automated
  hunts need the same duplicate discipline as registries (see the
  md5-identical pair above).

## Case 10: the animal kingdom repeats the human asymmetry (2026-09-01)

A licence-verified sweep for ANIMAL movement/symptom data (owner
directive: include it if it exists) found the same lopsidedness as the
human corpus, in the same direction. The hypokinetic/parkinsonian pole
is genuinely open: 6-OHDA and MitoPark mouse kinematic syllables
(CC BY, raw), a ~700-mouse pharmacological sweep spanning
haloperidol catalepsy to stimulant stereotypy (CC BY), alpha-synuclein
and SOD1 gait exports, macaque reach corpora. The hyperkinetic pole is
an open-data desert AGAIN: no open harmaline tremor recordings, no
dystonia-model kinematics (the one modern Tor1a/DYT1 behavioral study
is data-available-on-request), no tic-model video, no Huntington-model
raw kinematics (R6/2 and Q175 gait live only in supplementary tables;
the consortium platform is registration-gated), no dyskinesia video.
Veterinary movement data is proprietary end to end; fish and fly
disease-model locomotion is published without deposits.

Paper point: the scarcity gradient across the hyper/hypokinetic axis
is species-invariant. Whatever drives it (clinical rating culture,
video-privacy burden, lab tooling defaults), it reproduces in animal
research where privacy is not the explanation, which sharpens the
interpretation: hyperkinetic movement is systematically under-deposited,
not merely harder to de-identify.

## Case 11: "the data are with this article", and they are not (2026-09-02)

alphasyn_catwalk (Data in Brief 10.1016/j.dib.2017.12.067, CC BY,
alpha-synuclein transgenic mouse CatWalk gait): the Specifications
Table states "Data accessibility: The data are with this article". The
only file actually attached, identically on PMC (PMC5988224) and on the
Elsevier CDN, is mmc1.xlsx, 10.9 KB, whose three sheets (wt, ko,
huWT.KO) are a LIST of 120 per-run spreadsheet FILENAMES
('3626_Run004.xlsx', ...), not the runs; the article text announces 90
run files. Probing the CDN for mmc2 through mmc5 across xlsx/zip/docx
finds nothing, and ScienceDirect serves a 403 challenge to automated
readers, so the one unverified location is the publisher page rendered
in a human browser (the owner's one-click check; the CDN normally IS
what that page serves). Until the runs surface, the entry stays
index-only on disk.

Paper point: this is the purest form of the barrier family. Open
licence, zero technical protection, a data journal whose whole purpose
is the data, a compliance sentence asserting presence, and the data
object itself absent from every location the article points to. The
barrier is editorial workflow, not policy.

### Case 11 addendum: a false positive, dissolved by the browser check (sensefog, 2026-09-07)

The pattern needs its counter-example. sensefog (Mendeley
10.17632/c9ckcvjxc7.1, STN Percept LFP + EMG + motion during real
walking with FOG events) was classified case-11 on 2026-09-05: the
public API's root file listing answered zero files, and the record's
own GitHub documentation pointed back at the record - the full
circular-pointer signature. The scheduled browser check (2026-09-07)
refuted it: the page shows "Download All 1.87 GB", CC BY 4.0, 555
downloads. The API verdict was an API-SHAPE artifact: this record
keeps every file inside a BIDS-like folder tree (per-subject
sub-*/ses-*/{eeg,ieeg,motion}), and Mendeley's files endpoint lists
ONE FOLDER LEVEL at a time - a root listing of a fully-foldered
record is legitimately empty. The fetcher now walks the folder tree
(fetch_mendeley.py), and the fetch landed the same day, every file
verified against Mendeley's own per-file sha256. (Two transport
notes for the bestiary: the record-level "Download All" zip lives on
an S3 bucket that answers 403 to every non-browser client - the
per-file URLs are the scripted route; and one remote folder is
literally named "SenseFOG-main " with a trailing space, an illegal
directory name on Windows, which the fetcher must sanitize.)

Method point: a case-11 verdict reached through an API alone is
provisional until a human-shaped client has seen the page. The
2026-09-05 protocol already said so ("one owner-browser check of the
JS file tree to finish"); this addendum is that check's result, and
it moved a dataset from write-off to in-hand in two hours.

## Case 12: our own deposit, audited like a stranger's (2026-09-03/04)

The mirror image of every case above: the provenance failure we found
was OURS. CODY v1.0.0 (10.5281/zenodo.22232610), published 2026-09-01,
was audited at arm's length two days later with the same tooling we
point at other people's deposits (API metadata reads, range-reads of
zip central directories, cross-checks against the papers' PDFs). Four
findings: (1) the deposit never named its extraction pipelines - the
YOLOv8 COCO-17 keypoint time-series in dataset_0_labels_raw.zip were
described as "labels" only, and SAM 3 was not credited for the dense
extraction; (2) the CODY-2 pediatric inference keypoints (12 subjects)
were absent, so paper 2 was not reproducible from the record; (3) a
models.zip was listed in the description AND carried an md5 in
MD5SUMS.txt but was never uploaded - a phantom file in the record's
own manifest; (4) paper 3's status was overstated ("submitted" vs "in
preparation"). All corrected in v1.1.0 (10.5281/zenodo.22275553,
published 2026-09-04): archives renamed to carry study + pipeline
(*_cody_1_2_yolo, *_cody_3_sam3), the pediatric keypoints deposited
(dataset_2_timeseries_cody_2_yolo.zip, 48 MB), the models listing
removed (owner ruling: models are not deposited), description
corrected; the six carried-over archives are byte-identical to
v1.0.0 (md5-verified).

Paper point: provenance decay is not an us-versus-them phenomenon.
The same week we catalogued eleven external barrier patterns, our own
two-day-old deposit failed a provenance audit on four counts. The
difference is not who errs but who re-reads: deposits need the same
adversarial audit their authors would apply to a stranger's data, and
versioned repositories make the correction cheap (one new version DOI,
same concept DOI, full file-level diff on record).

## Case 13: withdrawn after publication, badges still green (piet_essential_tremor, 2026-09-07)

PIET (10.57760/sciencedb.28935, ScienceDB, published 2025-11-24: 45
essential-tremor patients, MP2RAGE structural + 5 rsfMRI runs each,
589 files) was catalogued 2026-09-04 and page-verified PUBLIC/CC0 on
2026-09-05, fetch queued behind the 000947 transfer. At fetch time two
days later the landing page still displays the PUBLIC badge and the
CC0 logo, and DataCite still serves the record as cc0-1.0 (SPDX) with
"30585040003 bytes / 589 files" - but the Data File Download section
now carries a "Dataset Withdrawal Statement": the dataset "is not
currently available for public access" per "relevant requirements of
the hospital"; inquiries go to the corresponding authors. The page's
own statistics panel records 21,486 file downloads before the gate
closed, and its info panel now reports 28.48 GB against the 30.6 GB
DataCite still advertises.

Two mechanics worth keeping separate. First, the withdrawal is visible
ONLY in the download section: DOI resolution, DataCite metadata,
licence badges and the description all continue to assert an open
dataset (contrast TIM-TREMOR, case study of the blunt variant, whose
source returns a bare 410). Second, and independent of the withdrawal,
ScienceDB login-walls its file-list API portal-wide: queryFileList
answers "User Not Login" even to an anonymous browser session on a
dataset that IS public (open-DBS, re-checked the same day: PUBLIC/CC0,
V2, no withdrawal), so even open ScienceDB sets require an account
before a single file name is visible - the anti-bot layer the closing
sweep noted is really an authentication layer.

Paper point: version-of-record decay observed in real time, inside a
48-hour window between two verifications of the same page. A CC0
declaration is irrevocable on copies already distributed (those 21,486
file downloads are legally clean) but says nothing about the source
staying open, and neither the repository's own badges nor DataCite
noticed the closure. Any catalogue that verifies a licence once and
caches the verdict will silently rot; the fetch-time re-verification
rule - which corrected 4 of 8 sweep licence guesses on 2026-09-05 -
caught a full withdrawal two days later. Verify at fetch, not at
catalogue time, and record what the page said on which date.
