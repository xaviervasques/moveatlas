# Leuven/Pellenberg 3D gait of children with CP (figshare)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Leuven/Pellenberg 3D gait of children with CP (figshare)",
 "description": "Leuven/Pellenberg 3D gait of children with CP (figshare). MoveAtlas pose family. 356 subjects. licence CC0 1.0.",
 "identifier": "https://doi.org/10.6084/m9.figshare.4877432",
 "license": "https://creativecommons.org/publicdomain/zero/1.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "D3 Pyramidal syndromes",
  "M1 Pose / video",
  "M3 Plantar force"
 ],
 "url": "https://doi.org/10.6084/m9.figshare.4877432",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 }
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-catalogued">catalogued</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>leuven_cp_gait</code>

<span class="ma-tag">Pyramidal syndromes</span><span class="ma-tag">Pose / video</span><span class="ma-tag">Plantar force</span>

| | |
|---|---|
| **Taxonomy cells** | D3 (cerebral palsy); M1 M3 |
| **Subjects** | 356 |
| **Status** | acquired (2026-09-06) |
| **License** | CC0 1.0 |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("leuven_cp_gait")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC0 1.0
- **Redistribution**: yes
- **Access route**: figshare 4877432
- **Source**: <https://doi.org/10.6084/m9.figshare.4877432>

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **MoveAtlas cells**: D3 (cerebral palsy); M1 M3
- **population**: children with unilateral or bilateral spastic CP, 3 to 18 years, GMFCS I to III, 1,719 gait trials (De Laet et al. 2017, PLoS One, doi 10.1371/journal.pone.0178378); 275 patients measured once and 81 more than once; the 56 typically developing children of that study are a reference average only, with no row in the workbook
- **n_subjects**: 356 (patient ids in the workbook's ALL sheet, and De Laet et al. 2017; the figshare description says 357, but its own breakdown of 275 + 67 + 14 patients sums to 356; set 2026-09-28, the field was empty)
