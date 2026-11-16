# Moore et al.: treadmill gait and the effect of mechanical perturbations

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Moore et al.: treadmill gait and the effect of mechanical perturbations",
 "description": "Moore et al.: treadmill gait and the effect of mechanical perturbations. MoveAtlas pose family. 15 subjects. licence CC0 1.0.",
 "identifier": "https://doi.org/10.5281/zenodo.13030",
 "license": "https://creativecommons.org/publicdomain/zero/1.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "C1 Normal adult movement",
  "M1 Pose / video",
  "M3 Plantar force",
  "M5 EMG"
 ],
 "url": "https://doi.org/10.5281/zenodo.13030",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>moore_perturbed_gait</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span><span class="ma-tag">Plantar force</span><span class="ma-tag">EMG</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1, M3, M5 |
| **Subjects** | 15 |
| **Ages** | 19-32 y |
| **Status** | acquired (2026-11-12) |
| **License** | CC0 1.0 (Zenodo 13030, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("moore_perturbed_gait")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC0 1.0 (Zenodo 13030, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only moore_perturbed_gait)
- **Source**: <https://doi.org/10.5281/zenodo.13030>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: moore_perturbed_gait
- **family**: pose
- **MoveAtlas cells**: C1; M1, M3, M5
- **population**: 15 healthy adults (subject ids 1 to 17 in the trial meta files; id 0 marks unloaded trials)
- **n_subjects**: 15
- **age**: 19-32 y
- **signal**: D-Flow mocap text export per trial: 47 (full) or 27 (lower) marker trajectories, force plates, EMG and accelerometer analog channels; trial meta YAML
- **license**: CC0 1.0 (Zenodo 13030, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only moore_perturbed_gait)
- **link**: https://doi.org/10.5281/zenodo.13030
- **citation**: Moore, Hnat and van den Bogert, An elaborate data set on human gait and the effect of mechanical perturbations (Zenodo, 2014), doi 10.5281/zenodo.13030
