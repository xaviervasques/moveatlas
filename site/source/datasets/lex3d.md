# 3D-LEX v1.0: ASL and NGT sign lexicons, Vicon markers and FBX animation

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "3D-LEX v1.0: ASL and NGT sign lexicons, Vicon markers and FBX animation",
 "description": "3D-LEX v1.0: ASL and NGT sign lexicons, Vicon markers and FBX animation. MoveAtlas pose family. 4 subjects. licence CC BY 4.0.",
 "identifier": "https://osf.io/cv276/",
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
 "url": "https://osf.io/cv276/",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-catalogued">catalogued</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>lex3d</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1 |
| **Subjects** | 4 |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 (OSF cv276 node licence, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("lex3d")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (OSF cv276 node licence, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only lex3d)
- **Source**: <https://osf.io/cv276/>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: lex3d
- **family**: pose
- **MoveAtlas cells**: C1; M1
- **population**: sign language signers (ASL and NGT lexicons); 4 distinct signer names on the first line of the marker CSVs (names not copied)
- **n_subjects**: 4
- **signal**: Vicon marker trajectories (CSV, *_V3D_MarkerData.csv) and FBX skeletal animation, per sign
- **license**: CC BY 4.0 (OSF cv276 node licence, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only lex3d)
- **link**: https://osf.io/cv276/
- **citation**: 3D-LEX v1.0: 3D Lexicons for American Sign Language and Sign Language of the Netherlands (OSF cv276)
