# Notre Dame: whole-body optical marker and ground reaction force data of non-cyclic activities

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Notre Dame: whole-body optical marker and ground reaction force data of non-cyclic activities",
 "description": "Notre Dame: whole-body optical marker and ground reaction force data of non-cyclic activities. MoveAtlas pose family. 10 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.7274/28689221.v1",
 "license": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "C1 Normal adult movement",
  "M1 Pose / video",
  "M3 Plantar force"
 ],
 "url": "https://doi.org/10.7274/28689221.v1",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>notredame_noncyclic</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span><span class="ma-tag">Plantar force</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1, M3 |
| **Subjects** | 10 |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 (CurateND 10.7274/28689221.v1, read at fetch 2026-11-12; the article is CC BY-NC-ND and covers the article only, not the data) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("notredame_noncyclic")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (CurateND 10.7274/28689221.v1, read at fetch 2026-11-12; the article is CC BY-NC-ND and covers the article only, not the data)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only notredame_noncyclic; the 10 participant zips)
- **Source**: <https://doi.org/10.7274/28689221.v1>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: notredame_noncyclic
- **family**: pose
- **MoveAtlas cells**: C1; M1, M3
- **population**: 10 healthy adults (AB01 to AB10)
- **n_subjects**: 10
- **signal**: 3D marker trajectories (48 to 57 landmarks, 200 Hz, metres), C3D; GRF; OpenSim models and results
- **license**: CC BY 4.0 (CurateND 10.7274/28689221.v1, read at fetch 2026-11-12; the article is CC BY-NC-ND and covers the article only, not the data); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only notredame_noncyclic; the 10 participant zips)
- **link**: https://doi.org/10.7274/28689221.v1
- **citation**: Whole-body optical marker and ground reaction force data of healthy humans performing non-cyclic activities (CurateND, 2025), doi 10.7274/28689221.v1
