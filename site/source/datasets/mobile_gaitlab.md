# mobile-gaitlab: video-derived gait keypoints of 1026 CP patients (Stanford/Gillette)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "mobile-gaitlab: video-derived gait keypoints of 1026 CP patients (Stanford/Gillette)",
 "description": "mobile-gaitlab: video-derived gait keypoints of 1026 CP patients (Stanford/Gillette). MoveAtlas pose family. 1026 subjects. licence data: CC BY-NC.",
 "identifier": "https://github.com/stanfordnmbl/mobile-gaitlab",
 "license": "https://creativecommons.org/licenses/by-nc/4.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "D3 Pyramidal syndromes",
  "C1 Normal adult movement",
  "M1 Pose / video"
 ],
 "url": "https://github.com/stanfordnmbl/mobile-gaitlab",
 "isAccessibleForFree": false,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-catalogued">catalogued</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>mobile_gaitlab</code>

<span class="ma-tag">Pyramidal syndromes</span><span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | D3 (cerebral palsy); C1; M1 |
| **Subjects** | 1026 |
| **Ages** | children (1994-2015 visits) |
| **Status** | catalogued (2026-09-05) |
| **License** | data: CC BY-NC (4.0 in the SimTK DataCite record 10.18735/j0rz-0k12, 2.0 in the GitHub README), trajectories and labels on SimTK, raw clinical video not published; code: Apache 2.0 (GitHub stanfordnmbl/mobile-gaitlab); the demo video of the repository and its keypoints are Gillette material for testing only |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("mobile_gaitlab")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: data: CC BY-NC (4.0 in the SimTK DataCite record 10.18735/j0rz-0k12, 2.0 in the GitHub README), trajectories and labels on SimTK, raw clinical video not published; code: Apache 2.0 (GitHub stanfordnmbl/mobile-gaitlab); the demo video of the repository and its keypoints are Gillette material for testing only
- **Redistribution**: unknown
- **Access route**: github stanfordnmbl/mobile-gaitlab
- **Source**: <https://github.com/stanfordnmbl/mobile-gaitlab>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **MoveAtlas cells**: D3 (cerebral palsy); C1; M1
- **population**: 1,026 patients with cerebral palsy, 1,792 clinical gait videos (Kidzinski et al. 2020, Nat Commun, doi 10.1038/s41467-020-17807-z); none of their trajectories is on disk
- **n_subjects**: 1026 (source count; not held)
