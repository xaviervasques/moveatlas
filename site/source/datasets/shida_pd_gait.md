# Shida et al.: overground walking full-body kinematics and kinetics in Parkinson's disease, ON and OFF medication (C3D)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Shida et al.: overground walking full-body kinematics and kinetics in Parkinson's disease, ON and OFF medication (C3D)",
 "description": "Shida et al.: overground walking full-body kinematics and kinetics in Parkinson's disease, ON and OFF medication (C3D). MoveAtlas pose family. 26 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.6084/m9.figshare.14896881.v4",
 "license": "https://creativecommons.org/licenses/by/4.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "B2 Bradykinesia",
  "B3 Hypokinesia",
  "B5 Freezing of gait",
  "M1 Pose / video",
  "M3 Plantar force",
  "M12 Clinical scales"
 ],
 "url": "https://doi.org/10.6084/m9.figshare.14896881.v4",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>shida_pd_gait</code>

<span class="ma-tag">Bradykinesia</span><span class="ma-tag">Hypokinesia</span><span class="ma-tag">Freezing of gait</span><span class="ma-tag">Pose / video</span><span class="ma-tag">Plantar force</span><span class="ma-tag">Clinical scales</span>

| | |
|---|---|
| **Taxonomy cells** | B2, B3, B5 (FoG-Q score and a FoG group per patient); M1, M3, M12 |
| **Subjects** | 26 |
| **Ages** | 44-81 y |
| **Status** | acquired (2026-11-12) |
| **License** | CC BY 4.0 (figshare 14896881 v4, read at fetch 2026-11-12) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("shida_pd_gait")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (figshare 14896881 v4, read at fetch 2026-11-12)
- **Redistribution**: yes
- **Access route**: direct_download (fetch_open_mocap.py fetch --only shida_pd_gait)
- **Source**: <https://doi.org/10.6084/m9.figshare.14896881.v4>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: shida_pd_gait
- **family**: pose
- **MoveAtlas cells**: B2, B3, B5 (FoG-Q score and a FoG group per patient); M1, M3, M12
- **population**: 26 people with Parkinson's disease (PDGinfo.xlsx: age 44-81 y, sex, disease duration, LEDD, Hoehn and Yahr, UPDRS, MoCA, mini-BESTest, FoG-Q per patient), each recorded OFF and ON medication
- **n_subjects**: 26
- **age**: 44-81 y
- **signal**: 3D marker trajectories (44 markers, 150 Hz) and force plates, C3D; Visual3D exports (CSV, MDH, V3S)
- **license**: CC BY 4.0 (figshare 14896881 v4, read at fetch 2026-11-12); redistribution: yes
- **access**: direct_download (fetch_open_mocap.py fetch --only shida_pd_gait)
- **link**: https://doi.org/10.6084/m9.figshare.14896881.v4
- **citation**: Shida et al., A dataset of overground walking full-body kinematics and kinetics in individuals with Parkinson's disease (figshare, v4), doi 10.6084/m9.figshare.14896881.v4
