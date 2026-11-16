# Horst et al.: overground walking, full-body kinematics and kinetics of healthy adults (C3D)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Horst et al.: overground walking, full-body kinematics and kinetics of healthy adults (C3D)",
 "description": "Horst et al.: overground walking, full-body kinematics and kinetics of healthy adults (C3D). MoveAtlas pose family. 57 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.17632/svx74xcrjr.3",
 "license": "https://creativecommons.org/licenses/by/4.0/",
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
 "url": "https://doi.org/10.17632/svx74xcrjr.3",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>horst_gait_fullbody</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span><span class="ma-tag">Plantar force</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1, M3 |
| **Subjects** | 57 |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 (Mendeley Data svx74xcrjr v3, DataCite, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("horst_gait_fullbody")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (Mendeley Data svx74xcrjr v3, DataCite, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only horst_gait_fullbody)
- **Source**: <https://doi.org/10.17632/svx74xcrjr.3>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: horst_gait_fullbody
- **family**: pose
- **MoveAtlas cells**: C1; M1, M3
- **population**: 57 healthy adults
- **n_subjects**: 57
- **signal**: 3D marker trajectories (54 markers, 250 Hz) and force plates, C3D
- **license**: CC BY 4.0 (Mendeley Data svx74xcrjr v3, DataCite, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only horst_gait_fullbody)
- **link**: https://doi.org/10.17632/svx74xcrjr.3
- **citation**: Horst et al., A public dataset of overground walking kinetics and full-body kinematics in healthy adult individuals (Mendeley Data, 2019), doi 10.17632/svx74xcrjr.3
