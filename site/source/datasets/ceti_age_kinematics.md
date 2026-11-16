# CeTI-Age-Kinematics: full-body inertial motion of older and younger adults in daily tasks

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "CeTI-Age-Kinematics: full-body inertial motion of older and younger adults in daily tasks",
 "description": "CeTI-Age-Kinematics: full-body inertial motion of older and younger adults in daily tasks. MoveAtlas pose family. 32 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.6084/m9.figshare.26983645.v2",
 "license": "https://creativecommons.org/licenses/by/4.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "C1 Normal adult movement",
  "C3 Aging",
  "M1 Pose / video",
  "M2 Inertial (IMU)"
 ],
 "url": "https://doi.org/10.6084/m9.figshare.26983645.v2",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>ceti_age_kinematics</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Aging</span><span class="ma-tag">Pose / video</span><span class="ma-tag">Inertial (IMU)</span>

| | |
|---|---|
| **Taxonomy cells** | C1, C3 (older adults); M1, M2 |
| **Subjects** | 32 |
| **Ages** | 19-28 y and 66-75 y |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 (figshare 10.6084/m9.figshare.26983645.v2, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("ceti_age_kinematics")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (figshare 10.6084/m9.figshare.26983645.v2, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only ceti_age_kinematics)
- **Source**: <https://doi.org/10.6084/m9.figshare.26983645.v2>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: ceti_age_kinematics
- **family**: pose
- **MoveAtlas cells**: C1, C3 (older adults); M1, M2
- **population**: 32 adults: 20 older (OA, 66-75 y) and 12 younger (YA, 19-28 y) (participants.tsv participant_group; ages as the README states)
- **n_subjects**: 32
- **age**: 19-28 y and 66-75 y
- **signal**: full-body inertial suit and gloves (Rokoko Smartsuit Pro, 19 suit IMUs, 7 per glove), exported as BVH skeletons (100 Hz) and per-segment TSV
- **license**: CC BY 4.0 (figshare 10.6084/m9.figshare.26983645.v2, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only ceti_age_kinematics)
- **link**: https://doi.org/10.6084/m9.figshare.26983645.v2
- **citation**: The CeTI-Age-Kinematics dataset: A Full-Body IMU-Based Motion Dataset of Daily Tasks by Older and Younger Adults (figshare, 2025), doi 10.6084/m9.figshare.26983645.v2
