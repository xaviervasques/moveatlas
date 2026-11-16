# 100STYLE: one actor, 100 locomotion styles (BVH)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "100STYLE: one actor, 100 locomotion styles (BVH)",
 "description": "100STYLE: one actor, 100 locomotion styles (BVH). MoveAtlas pose family. 1 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.5281/zenodo.8127870",
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
 "url": "https://doi.org/10.5281/zenodo.8127870",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>style100</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1 |
| **Subjects** | 1 |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 (Zenodo 8127870, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("style100")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (Zenodo 8127870, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only style100)
- **Source**: <https://doi.org/10.5281/zenodo.8127870>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: style100
- **family**: pose
- **MoveAtlas cells**: C1; M1
- **population**: one actor (dataset description)
- **n_subjects**: 1
- **signal**: BVH skeletal motion, 60 fps (Frame Time 0.016667 s), 23 joints, no fingers
- **license**: CC BY 4.0 (Zenodo 8127870, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only style100)
- **link**: https://doi.org/10.5281/zenodo.8127870
- **citation**: 100STYLE Dataset (Zenodo 8127870); article doi 10.1145/3522618
