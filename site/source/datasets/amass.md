# AMASS (healthy mocap base)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "AMASS (healthy mocap base)",
 "description": "AMASS (healthy mocap base). MoveAtlas socle family. licence non-commercial research.",
 "identifier": "https://amass.is.tue.mpg.de",
 "license": "non-commercial research (per sub-dataset MPI EULA)",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "socle",
  "C1 Normal adult movement",
  "M1 Pose / video"
 ],
 "url": "https://amass.is.tue.mpg.de",
 "isAccessibleForFree": false,
 "measurementTechnique": "socle",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-socle">socle</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>amass</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1 |
| **Subjects** | ~344 |
| **Status** | harmonized |
| **License** | non-commercial research (per sub-dataset MPI EULA) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("amass")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: non-commercial research (per sub-dataset MPI EULA)
- **Redistribution**: no
- **Access route**: account + EULA
- **Source**: <https://amass.is.tue.mpg.de>

## Publications

- Mahmood, Naureen; Ghorbani, Nima; Troje, Nikolaus F.; Pons-Moll, Gerard; Black, Michael (2019). *AMASS: Archive of Motion Capture As Surface Shapes*. 2019 IEEE/CVF International Conference on Computer Vision (ICCV). DOI: [10.1109/iccv.2019.00554](https://doi.org/10.1109/iccv.2019.00554)

```bibtex
@article{amass_paper_2019,
  title = {AMASS: Archive of Motion Capture As Surface Shapes},
  author = {Mahmood, Naureen and Ghorbani, Nima and Troje, Nikolaus F. and Pons-Moll, Gerard and Black, Michael},
  year = {2019},
  doi = {10.1109/iccv.2019.00554},
  journal = {2019 IEEE/CVF International Conference on Computer Vision (ICCV)}
}
```

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **known issues**: 404 of the 17,154 canonical records (242 in BMLhandball, 124 in BMLmovi and 38 in ACCAD, each at least 1,261 frames long) were not rigid skeletons in the shards built before 2026-09-29 (a bone length varied by more than 5 percent over the frames); joints recomputed from the source SMPL+H parameters differed from these 404 and reproduced the rigid records checked to 1e-4 torso units, so the fault was in the build, not the source. The three shards were rebuilt on 2026-09-29 by build_canonical_amass.py, which now refuses a skeleton whose bones change length: the 404 records are rigid (0 of the 17,154 records fail the 5 percent test), their order, frame counts and frame rates and both manifests are unchanged, and the other 21 subsets were not rebuilt. Anything computed from these takes before 2026-09-29 used non-rigid joints. The 2,914 records built from MoSh++ stage-II files (takes ending in _stageii.npz: every record of GRAB (1,340), SOMA (69), CNRS (79) and WEIZMANN (1,426)) were built with fps None and an empty fps cell in the manifests: these files state their rate under mocap_frame_rate (120 in every CNRS and WEIZMANN file), a key the builder reads only since 2026-10-05. The 79 CNRS and 1,426 WEIZMANN records carry 120.0, in their records and in both manifests, since 2026-11-10 (build_canonical_amass.py --only CNRS WEIZMANN --fill-fps, coordinates unchanged); the 1,409 GRAB and SOMA records still have fps None. CNRS and WEIZMANN are SMPL-X fits (surface_model_type smplx in every file; poses of 165 values per frame in the SMPL-X order root, body, jaw, eyes, hands), and the builder computed their joints with the SMPL+H model: the root and 21 body joint rotations are those of the fit, but the rest skeleton comes from the SMPL+H template and shape space driven by SMPL-X shape coefficients, so the bone proportions and joint offsets of these 1,505 records are not those of the fitted bodies; leave them out where body proportions matter. The two subsets stay in the canonical pool, flagged by this sentence, until they are built with the SMPL-X body model, which the repository does not hold. The builder skips every archive member whose file name contains "shape" or "neutral", a filter meant for the per-subject shape files that also leaves out 800 motions: 796 WEIZMANN S-shaped walks (*SShape*_stageii.npz, SMPL-X fits) and 4 DanceDB dances (*Neutral*_poses.npz); the 17,154 records hold none of them. They are to be added at the next release, with the SMPL-X build.
