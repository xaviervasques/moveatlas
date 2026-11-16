# Push recovery: full-body motion capture after external perturbations from five directions (C3D)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Push recovery: full-body motion capture after external perturbations from five directions (C3D)",
 "description": "Push recovery: full-body motion capture after external perturbations from five directions (C3D). MoveAtlas pose family. 21 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.5281/zenodo.10512652",
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
 "url": "https://doi.org/10.5281/zenodo.10512652",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>push_recovery_perturbations</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1 |
| **Subjects** | 21 |
| **Ages** | 20-38 y |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 (Zenodo 10512652, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("push_recovery_perturbations")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (Zenodo 10512652, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only push_recovery_perturbations)
- **Source**: <https://doi.org/10.5281/zenodo.10512652>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: push_recovery_perturbations
- **family**: pose
- **MoveAtlas cells**: C1; M1
- **population**: 21 healthy young adults (10 women, 11 men), 20-38 y (ReadMe)
- **n_subjects**: 21
- **age**: 20-38 y
- **signal**: 3D marker trajectories (40 body markers and 3 pole markers, Qualisys, 200 Hz), C3D, and CSV exports
- **license**: CC BY 4.0 (Zenodo 10512652, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only push_recovery_perturbations)
- **link**: https://doi.org/10.5281/zenodo.10512652
- **citation**: Chatagnon et al., Full Body Motion Capture of Single Individuals Following External Perturbations from Different Directions (Zenodo, 2024), doi 10.5281/zenodo.10512652; article doi 10.1016/j.jbiomech.2023.111703 (ReadMe)
