# CMU Graphics Lab Motion Capture Database (C3D)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "CMU Graphics Lab Motion Capture Database (C3D)",
 "description": "CMU Graphics Lab Motion Capture Database (C3D). MoveAtlas pose family. 109 subjects. licence CMU Graphics Lab Motion Capture Database terms.",
 "identifier": "http://mocap.cs.cmu.edu/",
 "license": "CMU Graphics Lab Motion Capture Database terms (mocap.cs.cmu.edu, read at fetch 2026-11-12): free for all uses; may be c",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "C1 Normal adult movement",
  "M1 Pose / video"
 ],
 "url": "http://mocap.cs.cmu.edu/",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>cmu_mocap</code>

<span class="ma-tag">Normal adult movement</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | C1; M1 |
| **Subjects** | 109 |
| **Status** | acquired (2026-11-12) |
| **License** | CMU Graphics Lab Motion Capture Database terms (mocap.cs.cmu.edu, read at fetch 2026-11-12): free for all uses; may be copied, modified or redistributed without permission (FAQ); may not be resold directly, even in converted form (home page). Not a Creative Commons licence. No NC condition (commercial use is allowed; only resale of the data itself is excluded) and no ND condition (modification and... |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("cmu_mocap")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CMU Graphics Lab Motion Capture Database terms (mocap.cs.cmu.edu, read at fetch 2026-11-12): free for all uses; may be copied, modified or redistributed without permission (FAQ); may not be resold directly, even in converted form (home page). Not a Creative Commons licence. No NC condition (commercial use is allowed; only resale of the data itself is excluded) and no ND condition (modification and
- **Redistribution**: yes (no direct resale of the data, even converted; the no-resale sentence travels with any copy)
- **Access route**: direct_download (fetch_open_mocap.py fetch --only cmu_mocap; C3D zips only)
- **Source**: <http://mocap.cs.cmu.edu/>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: cmu_mocap
- **family**: pose
- **MoveAtlas cells**: C1; M1
- **population**: healthy performers (actors, dancers, athletes and lab members) in 109 subject folders
- **n_subjects**: 109
- **signal**: 3D marker trajectories, 41-marker Vicon full-body set (41 to 674 points per file with unlabelled and virtual points), C3D
- **license**: CMU Graphics Lab Motion Capture Database terms (mocap.cs.cmu.edu, read at fetch 2026-11-12): free for all uses; may be copied, modified or redistributed without permission (FAQ); may not be resold directly, even in converted form (home page). Not a Creative Commons licence. No NC condition (commercial use is allowed; only resale of the data itself is excluded) and no ND condition (modification and conversion are allowed): open under the program's definition, with the no-resale sentence carried into any release; redistribution: yes (no direct resale of the data, even converted; the no-resale sentence travels with any copy)
- **access**: direct_download (fetch_open_mocap.py fetch --only cmu_mocap; C3D zips only)
- **link**: http://mocap.cs.cmu.edu/
- **citation**: CMU Graphics Lab Motion Capture Database, http://mocap.cs.cmu.edu/ (no DOI)
