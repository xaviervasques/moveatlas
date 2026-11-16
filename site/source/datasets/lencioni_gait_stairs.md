# Lencioni et al.: kinematic, kinetic and EMG data of walking variants and stairs

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Lencioni et al.: kinematic, kinetic and EMG data of walking variants and stairs",
 "description": "Lencioni et al.: kinematic, kinetic and EMG data of walking variants and stairs. MoveAtlas pose family. 50 subjects. licence CC BY 4.0 applied: every figshare item of collection 10.6084.",
 "identifier": "https://doi.org/10.6084/m9.figshare.c.4494755.v1",
 "license": "https://creativecommons.org/publicdomain/zero/1.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "C1 Normal adult movement",
  "C2 Infant development",
  "M1 Pose / video",
  "M3 Plantar force",
  "M5 EMG"
 ],
 "url": "https://doi.org/10.6084/m9.figshare.c.4494755.v1",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>lencioni_gait_stairs</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Infant development</span><span class="ma-tag">Pose / video</span><span class="ma-tag">Plantar force</span><span class="ma-tag">EMG</span>

| | |
|---|---|
| **Taxonomy cells** | C1, C2 (children from 6 y); M1, M3, M5 |
| **Subjects** | 50 |
| **Ages** | 6-72 y |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 applied: every figshare item of collection 10.6084/m9.figshare.c.4494755 states CC0, the data paper states CC BY 4.0 (read at fetch 2026-11-12); the stricter, attribution-requiring CC BY 4.0 is applied |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("lencioni_gait_stairs")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 applied: every figshare item of collection 10.6084/m9.figshare.c.4494755 states CC0, the data paper states CC BY 4.0 (read at fetch 2026-11-12); the stricter, attribution-requiring CC BY 4.0 is applied
- **Redistribution**: yes (with attribution, CC BY 4.0 applied)
- **Access route**: direct_download (fetch_open_mocap.py fetch --only lencioni_gait_stairs)
- **Source**: <https://doi.org/10.6084/m9.figshare.c.4494755.v1>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: lencioni_gait_stairs
- **family**: pose
- **MoveAtlas cells**: C1, C2 (children from 6 y); M1, M3, M5
- **population**: 50 healthy subjects, 6-72 y
- **n_subjects**: 50
- **age**: 6-72 y
- **signal**: per-trial marker trajectories (29 markers, LAMB total-body protocol), GRF, EMG, joint angles, moments and powers in one MATLAB struct per subject
- **license**: CC BY 4.0 applied: every figshare item of collection 10.6084/m9.figshare.c.4494755 states CC0, the data paper states CC BY 4.0 (read at fetch 2026-11-12); the stricter, attribution-requiring CC BY 4.0 is applied; redistribution: yes (with attribution, CC BY 4.0 applied)
- **access**: direct_download (fetch_open_mocap.py fetch --only lencioni_gait_stairs)
- **link**: https://doi.org/10.6084/m9.figshare.c.4494755.v1
- **citation**: Lencioni et al., Human kinematic, kinetic and EMG data during level walking, toe/heel-walking, stairs ascending/descending (figshare collection, 2019), doi 10.6084/m9.figshare.c.4494755.v1
