# DeepDance: motion capture of improvised dance (Qualisys TSV)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "DeepDance: motion capture of improvised dance (Qualisys TSV)",
 "description": "DeepDance: motion capture of improvised dance (Qualisys TSV). MoveAtlas pose family. 30 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.5281/zenodo.7950401",
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
 "url": "https://doi.org/10.5281/zenodo.7950401",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>deepdance</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1 |
| **Subjects** | 30 |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 (Zenodo 7950401, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("deepdance")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (Zenodo 7950401, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only deepdance)
- **Source**: <https://doi.org/10.5281/zenodo.7950401>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: deepdance
- **family**: pose
- **MoveAtlas cells**: C1; M1
- **population**: 30 dancers (file prefixes Subject1 to Subject30, plus Subject001 read as subject 1)
- **n_subjects**: 30
- **signal**: 3D marker trajectories (42 or 43 markers, Qualisys, 240 or 250 Hz), one TSV per one-minute take
- **license**: CC BY 4.0 (Zenodo 7950401, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only deepdance)
- **link**: https://doi.org/10.5281/zenodo.7950401
- **citation**: DeepDance: Motion capture data of improvised dance (2019) (Zenodo 7950401, v2.0), doi 10.5281/zenodo.7950401
