# Van der Zee et al.: healthy walking at 33 speed, step length and step width conditions (level 1 C3D)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Van der Zee et al.: healthy walking at 33 speed, step length and step width conditions (level 1 C3D)",
 "description": "Van der Zee et al.: healthy walking at 33 speed, step length and step width conditions (level 1 C3D). MoveAtlas pose family. 10 subjects. licence CC0 1.0.",
 "identifier": "https://doi.org/10.6084/m9.figshare.c.5897423.v1",
 "license": "https://creativecommons.org/publicdomain/zero/1.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "C1 Normal adult movement",
  "M1 Pose / video"
 ],
 "url": "https://doi.org/10.6084/m9.figshare.c.5897423.v1",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>vanderzee_walking</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1 |
| **Subjects** | 10 |
| **Status** | acquired (2026-11-12) |
| **License** | CC0 1.0 (figshare collection 10.6084/m9.figshare.c.5897423, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("vanderzee_walking")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC0 1.0 (figshare collection 10.6084/m9.figshare.c.5897423, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only vanderzee_walking; level 1 C3D only)
- **Source**: <https://doi.org/10.6084/m9.figshare.c.5897423.v1>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: vanderzee_walking
- **family**: pose
- **MoveAtlas cells**: C1; M1
- **population**: 10 healthy young adults
- **n_subjects**: 10
- **signal**: 3D marker trajectories (35 markers, 120 Hz), level 1 C3D
- **license**: CC0 1.0 (figshare collection 10.6084/m9.figshare.c.5897423, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only vanderzee_walking; level 1 C3D only)
- **link**: https://doi.org/10.6084/m9.figshare.c.5897423.v1
- **citation**: Van der Zee et al., A biomechanics dataset of healthy human walking at various speeds, step lengths and step widths (figshare collection, 2022), doi 10.6084/m9.figshare.c.5897423.v1
