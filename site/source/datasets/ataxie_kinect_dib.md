# Ataxia gait Kinect (Summa 2020)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "Ataxia gait Kinect (Summa 2020)",
 "description": "Ataxia gait Kinect (Summa 2020). MoveAtlas pose family. 51 subjects. licence CC BY 4.0.",
 "identifier": "https://doi.org/10.1016/j.dib.2020.106307",
 "license": "https://creativecommons.org/licenses/by/4.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "pose",
  "D2 Ataxia",
  "M1 Pose / video"
 ],
 "url": "https://doi.org/10.1016/j.dib.2020.106307",
 "isAccessibleForFree": true,
 "measurementTechnique": "pose",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 },
 "creator": [
  {
   "@type": "Person",
   "name": "Summa, S."
  },
  {
   "@type": "Person",
   "name": "Tartarisco, G."
  },
  {
   "@type": "Person",
   "name": "Favetta, M."
  },
  {
   "@type": "Person",
   "name": "Buzachis, A."
  },
  {
   "@type": "Person",
   "name": "Romano, A."
  },
  {
   "@type": "Person",
   "name": "Bernava, G.M."
  },
  {
   "@type": "Person",
   "name": "Vasco, G."
  },
  {
   "@type": "Person",
   "name": "Pioggia, G."
  },
  {
   "@type": "Person",
   "name": "Petrarca, M."
  },
  {
   "@type": "Person",
   "name": "Castelli, E."
  },
  {
   "@type": "Person",
   "name": "Bertini, E."
  },
  {
   "@type": "Person",
   "name": "Schirinzi, T."
  }
 ]
}
</script>
```

<span class="ma-fam ma-pose">pose</span>&nbsp; <span class="ma-badge ma-catalogued">catalogued</span>&nbsp; <span class="ma-badge ma-recipe">recipe</span>&nbsp; <code>ataxie_kinect_dib</code>

<span class="ma-tag">Ataxia</span><span class="ma-tag">Pose / video</span>

| | |
|---|---|
| **Taxonomy cells** | D2; M1 (table only on disk) |
| **Subjects** | 51 |
| **Status** | catalogued |
| **License** | CC BY 4.0 (the Data in Brief article, whose data are its supplementary table mmc1.xlsx: Data accessibility With the article; the article licence is CC BY 4.0 per Crossref and Europe PMC PMC7498847, read 2026-11-10) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("ataxie_kinect_dib")
ds.info   # recipe: get_data() explains the route
```

## License and access

- **License**: CC BY 4.0 (the Data in Brief article, whose data are its supplementary table mmc1.xlsx: Data accessibility With the article; the article licence is CC BY 4.0 per Crossref and Europe PMC PMC7498847, read 2026-11-10)
- **Redistribution**: yes (with attribution to Summa et al. 2020)
- **Access route**: downloaded (table only)
- **Source**: <https://doi.org/10.1016/j.dib.2020.106307>

## Publications

- Summa, S.; Tartarisco, G.; Favetta, M.; Buzachis, A.; Romano, A.; Bernava, G.M.; Vasco, G.; Pioggia, G.; Petrarca, M.; Castelli, E.; Bertini, E.; Schirinzi, T. (2020). *Spatio-temporal parameters of ataxia gait dataset obtained with the Kinect*. Data in Brief. DOI: [10.1016/j.dib.2020.106307](https://doi.org/10.1016/j.dib.2020.106307)

```bibtex
@misc{ataxie_kinect_dib_data_2020,
  title = {Spatio-temporal parameters of ataxia gait dataset obtained with the Kinect},
  author = {Summa, S. and Tartarisco, G. and Favetta, M. and Buzachis, A. and Romano, A. and Bernava, G.M. and Vasco, G. and Pioggia, G. and Petrarca, M. and Castelli, E. and Bertini, E. and Schirinzi, T.},
  year = {2020},
  doi = {10.1016/j.dib.2020.106307},
  howpublished = {Data in Brief},
  note = {dataset}
}
```

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: ataxie_kinect_dib
- **family**: pose
- **MoveAtlas cells**: D2; M1 (table only on disk)
- **population**: 31 patients with ataxia (15 progressive, 16 chronic) and 20 healthy controls, SARA-scored (Summa et al. 2020, Data in Brief 32:106307)
- **n_subjects**: 51
- **signal**: clinical table (the article's supplementary mmc1.xlsx, on disk as raw/gait_parameters_ataxia_kinect.xlsx: spatio-temporal gait parameters, group, diagnosis and SARA for 51 participants); the Kinect v2 skeleton signal was never published
- **license**: CC BY 4.0 (the Data in Brief article, whose data are its supplementary table mmc1.xlsx: Data accessibility With the article; the article licence is CC BY 4.0 per Crossref and Europe PMC PMC7498847, read 2026-11-10); redistribution: yes (with attribution to Summa et al. 2020)
- **access**: downloaded (table only)
- **link**: https://doi.org/10.1016/j.dib.2020.106307
