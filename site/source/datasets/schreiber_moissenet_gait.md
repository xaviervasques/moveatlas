# Schreiber and Moissenet: gait at five walking speeds in injury-free adults (C3D)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Schreiber and Moissenet: gait at five walking speeds in injury-free adults (C3D)",
 "description": "Schreiber and Moissenet: gait at five walking speeds in injury-free adults (C3D). MoveAtlas pose family. 50 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.6084/m9.figshare.7734767.v8",
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
 "url": "https://doi.org/10.6084/m9.figshare.7734767.v8",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>schreiber_moissenet_gait</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1 |
| **Subjects** | 50 |
| **Ages** | 19-67 y |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 (figshare 7734767 v8, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("schreiber_moissenet_gait")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (figshare 7734767 v8, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only schreiber_moissenet_gait)
- **Source**: <https://doi.org/10.6084/m9.figshare.7734767.v8>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: schreiber_moissenet_gait
- **family**: pose
- **MoveAtlas cells**: C1; M1
- **population**: 50 injury-free adults, 19-67 y
- **n_subjects**: 50
- **age**: 19-67 y
- **signal**: 3D marker trajectories (52 anatomical landmarks, ISB codes, 100 Hz), C3D
- **license**: CC BY 4.0 (figshare 7734767 v8, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only schreiber_moissenet_gait)
- **link**: https://doi.org/10.6084/m9.figshare.7734767.v8
- **citation**: Schreiber and Moissenet, A multimodal dataset of human gait at different walking speeds established on injury-free adult participants (figshare, v8), doi 10.6084/m9.figshare.7734767.v8
