# UMONS-TAICHI: motion capture of Taijiquan gestures across expertise levels (C3D)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "UMONS-TAICHI: motion capture of Taijiquan gestures across expertise levels (C3D)",
 "description": "UMONS-TAICHI: motion capture of Taijiquan gestures across expertise levels (C3D). MoveAtlas pose family. 12 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.5281/zenodo.2784581",
 "license": "https://creativecommons.org/licenses/by/4.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "C1 Normal adult movement",
  "M1 Pose / video"
 ],
 "url": "https://doi.org/10.5281/zenodo.2784581",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>umons_taichi</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1 |
| **Subjects** | 12 |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 (Zenodo 2784581, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("umons_taichi")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (Zenodo 2784581, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only umons_taichi)
- **Source**: <https://doi.org/10.5281/zenodo.2784581>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: umons_taichi
- **family**: pose
- **MoveAtlas cells**: C1; M1
- **population**: 12 participants of different Taijiquan expertise
- **n_subjects**: 12
- **signal**: 3D marker trajectories (68 markers, 179 Hz), C3D; segmentation labels (.lab)
- **license**: CC BY 4.0 (Zenodo 2784581, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only umons_taichi)
- **link**: https://doi.org/10.5281/zenodo.2784581
- **citation**: UMONS-TAICHI: A multimodal motion capture dataset of expertise in Taijiquan gestures (Zenodo 2784581); article doi 10.1016/j.dib.2018.05.088
