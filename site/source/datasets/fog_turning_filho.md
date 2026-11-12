# FoG turning-in-place (Filho 2022)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "FoG turning-in-place (Filho 2022)",
 "description": "FoG turning-in-place (Filho 2022). MoveAtlas pose family. 35 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.6084/m9.figshare.14984667",
 "license": "https://creativecommons.org/publicdomain/zero/1.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "B5 Freezing of gait",
  "M1 Pose / video",
  "M2 Inertial (IMU)"
 ],
 "url": "https://doi.org/10.6084/m9.figshare.14984667",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 },
 "creator": [
  {
   "@type": "Person",
   "name": "Boari, Daniel"
  }
 ]
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-hosted">hosted</span>&nbsp; <code>fog_turning_filho</code>

<span class="ma-tag">Freezing of gait</span><span class="ma-tag">Pose / video</span><span class="ma-tag">Inertial (IMU)</span>

| | |
|---|---|
| **Taxonomy cells** | B5; M1, M2 (source video and IMU; MoveAtlas holds the IMU only) |
| **Subjects** | 35 |
| **Status** | harmonized |
| **License** | CC BY 4.0 (figshare item 14984667; the API states CC BY 4.0; verified 2026-09-16; an earlier CC0 reading was wrong) |
| **MoveAtlas record** | [10.5281/zenodo.22790322](https://doi.org/10.5281/zenodo.22790322) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("fog_turning_filho")
records, meta = ds.get_data()
```

## License and access

- **License**: CC BY 4.0 (figshare item 14984667; the API states CC BY 4.0; verified 2026-09-16; an earlier CC0 reading was wrong)
- **Redistribution**: yes
- **Access route**: downloaded
- **Source**: <https://doi.org/10.6084/m9.figshare.14984667>

## Publications

- Boari, Daniel (2022). *A public dataset of video, acceleration, angular velocity, and clinical scales in individuals with Parkinson's disease during the turning-in-place task*. figshare. DOI: [10.6084/m9.figshare.14984667](https://doi.org/10.6084/m9.figshare.14984667)
- Ribeiro De Souza, Caroline; Miao, Runfeng; Ávila De Oliveira, Júlia; Cristina De Lima-Pardini, Andrea; Fragoso De Campos, Débora; Silva-Batista, Carla; Teixeira, Luis; Shokur, Solaiman; Mohamed, Bouri; Coelho, Daniel Boari (2022). *A Public Data Set of Videos, Inertial Measurement Unit, and Clinical Scales of Freezing of Gait in Individuals With Parkinson's Disease During a Turning-In-Place Task*. Frontiers in Neuroscience. DOI: [10.3389/fnins.2022.832463](https://doi.org/10.3389/fnins.2022.832463)

```bibtex
@misc{fog_turning_filho_data_2022,
  title = {A public dataset of video, acceleration, angular velocity, and clinical scales in individuals with Parkinson's disease during the turning-in-place task},
  author = {Boari, Daniel},
  year = {2022},
  doi = {10.6084/m9.figshare.14984667},
  howpublished = {figshare},
  note = {dataset}
}
@article{fog_turning_filho_paper_2022,
  title = {A Public Data Set of Videos, Inertial Measurement Unit, and Clinical Scales of Freezing of Gait in Individuals With Parkinson's Disease During a Turning-In-Place Task},
  author = {Ribeiro De Souza, Caroline and Miao, Runfeng and Ávila De Oliveira, Júlia and Cristina De Lima-Pardini, Andrea and Fragoso De Campos, Débora and Silva-Batista, Carla and Teixeira, Luis and Shokur, Solaiman and Mohamed, Bouri and Coelho, Daniel Boari},
  year = {2022},
  doi = {10.3389/fnins.2022.832463},
  journal = {Frontiers in Neuroscience}
}
```

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: fog_turning_filho
- **family**: pose
- **MoveAtlas cells**: B5; M1, M2 (source video and IMU; MoveAtlas holds the IMU only)
- **population**: 35 PD with FoG (paper: a convenience sample of 35 patients, 16 female and 19 male; PDFEinfo.csv holds PDFE01 to PDFE35); age, disease duration, LEDD, more-affected side
- **n_subjects**: 35 (corrected 2026-09-24; 50 did not come from the source)
- **signal**: one Physilog 5 IMU (Gait Up) on the shank of the more affected side at 128 Hz (source files: ACC ML/AP/SI in g, GYR ML/AP/SI in deg/s; the records carry ACC ML/AP/SI and GYR ML/AP) and one Sony camera at 30 Hz filming the lower limbs; turning in place, recorded ON medication, on up to three visits one month apart; MoveAtlas holds the IMU only (106 records: 71 turning recordings of 120 s and 35 standing recordings)
- **license**: CC BY 4.0 (figshare item 14984667; the API states CC BY 4.0; verified 2026-09-16; an earlier CC0 reading was wrong); redistribution: yes
- **access**: downloaded
- **link**: https://doi.org/10.6084/m9.figshare.14984667
- **citation**: Frontiers in Neuroscience 2022, doi 10.3389/fnins.2022.832463
- **library recipe**: `moveatlas.fetch("fog_turning_filho")` (figshare answers programs with a browser challenge; fetch() names the file to save where and accepts it once there) then `moveatlas.ingest("fog_turning_filho")`, which writes the 106 IMU records under THIS path (datasets/pose/fog_turning_filho/processed/), where moveatlas.dataset() looks.
- **ingestion**: build_canonical_imu.py (fog_turning mapping) writes to datasets/imu/fog_turning_filho/processed/; the 106 records on disk and in the published record sit under datasets/pose/fog_turning_filho/processed/canonical_imu.npz, the path the library recipe writes and moveatlas.dataset() reads (checked 2026-09-28)
- **known issues**: the records declare the sensor location lower_back, but the single IMU sits on the shank of the more affected side (data paper, Methods; the side per patient is in PDFEinfo.csv); the records leave out two columns of the source IMU files, the third gyroscope axis (GYR SI) and the per-sample freezing flag; that flag and the PDFEinfo episode table are one consensus annotation of the video by two movement disorder specialists, carried to the IMU timeline by a procedure the source does not describe, with no inter-rater agreement reported
