# Sign Language Mocap Archive (Studio Galt): catalogue snapshot

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Sign Language Mocap Archive (Studio Galt): catalogue snapshot",
 "description": "Sign Language Mocap Archive (Studio Galt): catalogue snapshot. MoveAtlas pose family. 1 subjects. licence CC BY 4.0 applied: the Zenodo snapshot 24149408 states CC BY.",
 "identifier": "https://doi.org/10.5281/zenodo.24149408",
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
 "url": "https://doi.org/10.5281/zenodo.24149408",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-catalogued">catalogued</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>sign_language_mocap_archive</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1 (catalogue only) |
| **Subjects** | 1 |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 applied: the Zenodo snapshot 24149408 states CC BY 4.0, the GitHub repository states CC0-1.0 (read at fetch 2026-11-12); the stricter, attribution-requiring CC BY 4.0 is applied |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("sign_language_mocap_archive")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 applied: the Zenodo snapshot 24149408 states CC BY 4.0, the GitHub repository states CC0-1.0 (read at fetch 2026-11-12); the stricter, attribution-requiring CC BY 4.0 is applied
- **Redistribution**: yes (with attribution, CC BY 4.0 applied)
- **Access route**: direct_download (fetch_open_mocap.py fetch --only sign_language_mocap_archive)
- **Source**: <https://doi.org/10.5281/zenodo.24149408>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: sign_language_mocap_archive
- **family**: pose
- **MoveAtlas cells**: C1; M1 (catalogue only)
- **population**: one signer (dataset description)
- **n_subjects**: 1
- **signal**: catalogue and documentation of an archive of about 2,700 ASL motions (inertial suit and gloves, FBX); this snapshot holds no motion file
- **license**: CC BY 4.0 applied: the Zenodo snapshot 24149408 states CC BY 4.0, the GitHub repository states CC0-1.0 (read at fetch 2026-11-12); the stricter, attribution-requiring CC BY 4.0 is applied; redistribution: yes (with attribution, CC BY 4.0 applied)
- **access**: direct_download (fetch_open_mocap.py fetch --only sign_language_mocap_archive)
- **link**: https://doi.org/10.5281/zenodo.24149408
- **citation**: Sign Language Mocap Archive (Zenodo 24149408, snapshot 2026-11-11), doi 10.5281/zenodo.24149408
