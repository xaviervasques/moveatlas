# WearGait-PD (FDA/CDRH, Synapse syn52540892)

```{raw} html
<script type="application/ld+json">
{
 "@context": "https://schema.org",
 "@type": "Dataset",
 "name": "WearGait-PD (FDA/CDRH, Synapse syn52540892)",
 "description": "WearGait-PD (FDA/CDRH, Synapse syn52540892). MoveAtlas imu family. 185 subjects. licence CC BY 4.0.",
 "identifier": "https://www.synapse.org/Synapse:syn52540892",
 "license": "https://creativecommons.org/licenses/by/4.0/",
 "sdPublisher": {
  "@type": "Organization",
  "name": "MoveAtlas"
 },
 "keywords": [
  "imu",
  "B2 Bradykinesia",
  "B3 Hypokinesia",
  "C1 Normal adult movement",
  "M2 Inertial (IMU)",
  "M3 Plantar force"
 ],
 "url": "https://www.synapse.org/Synapse:syn52540892",
 "isAccessibleForFree": true,
 "measurementTechnique": "imu",
 "includedInDataCatalog": {
  "@type": "DataCatalog",
  "name": "MoveAtlas"
 },
 "creator": [
  {
   "@type": "Person",
   "name": "Kontson, Kimberly"
  },
  {
   "@type": "Person",
   "name": "Butala, Ankur"
  },
  {
   "@type": "Person",
   "name": "Muir, Brittney"
  },
  {
   "@type": "Person",
   "name": "Anderson, Anthony"
  },
  {
   "@type": "Person",
   "name": "Caiola, Michael"
  },
  {
   "@type": "Person",
   "name": "Eguren, David"
  },
  {
   "@type": "Person",
   "name": "Gonzalez, Michael"
  },
  {
   "@type": "Person",
   "name": "Motely, Seneca"
  },
  {
   "@type": "Person",
   "name": "Mills, Kelly"
  },
  {
   "@type": "Person",
   "name": "Moro Velazquez, Laureano"
  },
  {
   "@type": "Person",
   "name": "Dehak, Najim"
  },
  {
   "@type": "Person",
   "name": "Moukheiber, Emile"
  }
 ]
}
</script>
```

<span class="ma-fam ma-imu">imu</span>&nbsp; <span class="ma-badge ma-harmonized">harmonized</span>&nbsp; <span class="ma-badge ma-hosted">hosted</span>&nbsp; <code>weargait_pd</code>

<span class="ma-tag">Bradykinesia</span><span class="ma-tag">Hypokinesia</span><span class="ma-tag">Normal adult movement</span><span class="ma-tag">Inertial (IMU)</span><span class="ma-tag">Plantar force</span>

| | |
|---|---|
| **Taxonomy cells** | B2, B3, C1 (age-matched controls); M2, M3 |
| **Subjects** | 185 |
| **Status** | harmonized |
| **License** | CC BY 4.0 |
| **MoveAtlas record** | [10.5281/zenodo.24274992](https://doi.org/10.5281/zenodo.24274992) |

Cell codes are defined on the {doc}`taxonomy page </taxonomy>`.

## How to load

```python
import moveatlas
ds = moveatlas.dataset("weargait_pd")
records, meta = ds.get_data()
```

## License and access

- **License**: CC BY 4.0
- **Redistribution**: yes
- **Access route**: registration (free Synapse account + click-through)
- **Source**: <https://www.synapse.org/Synapse:syn52540892>

## Publications

- Kontson, Kimberly; Butala, Ankur; Muir, Brittney; Anderson, Anthony; Caiola, Michael; Eguren, David; Gonzalez, Michael; Motely, Seneca; Mills, Kelly; Moro Velazquez, Laureano; Dehak, Najim; Moukheiber, Emile (2024). *Wearables for gait in Parkinson's Disease and age-matched controls*. Synapse. DOI: [10.7303/syn52540892](https://doi.org/10.7303/syn52540892)

```bibtex
@misc{weargait_pd_data_2024,
  title = {Wearables for gait in Parkinson's Disease and age-matched controls},
  author = {Kontson, Kimberly and Butala, Ankur and Muir, Brittney and Anderson, Anthony and Caiola, Michael and Eguren, David and Gonzalez, Michael and Motely, Seneca and Mills, Kelly and Moro Velazquez, Laureano and Dehak, Najim and Moukheiber, Emile},
  year = {2024},
  doi = {10.7303/syn52540892},
  howpublished = {Synapse},
  note = {dataset}
}
```

## Data card

The dataset's card, factual lines; the full card with its verification dates, download journal and processing notes is in the repository.

- **dataset**: weargait_pd
- **family**: imu
- **MoveAtlas cells**: B2, B3, C1 (age-matched controls); M2, M3
- **population**: 100 PD + 85 age-matched controls, 1,458 gait/balance trials
- **n_subjects**: 185
- **signal**: 13 Xsens IMUs (full 9-axis) + Moticon insoles (16 cells/foot) + walkway + video, all 100 Hz
- **license**: CC BY 4.0; redistribution: yes
- **access**: registration (free Synapse account + click-through)
- **link**: https://www.synapse.org/Synapse:syn52540892
- **ingestion**: build_canonical_imu.py + build_canonical_force.py (totals-only)
- **known issues**: the source exports gyroscope rates in rad/s and magnetometer values normalized to the local field; records built from 2026-09-17 carry the gyroscope in deg/s, keep the magnetometer as recorded (declared in mag_unit) and mark sensor dropouts in sample_valid instead of writing zeros (earlier records held 20 partly missing accelerometer traces in m/s2 under the unit g). The force records (per-foot insole totals) have no source LTotalForce or RTotalForce value while an insole is not streaming (in all 1,362 recordings, as a run at the start of 1,358 of them; 8.6 percent of the foot samples): records built from 2026-09-29 store those samples as 0 N and mark them False in sample_valid, per foot; earlier records wrote 0 N with no mask, so in them read 0 N on both feet as missing, and 0 N on one foot as possibly missing. Three subject ids keep the suffix " (control)" of the source CSV file names (weargait:NLS145 (control), weargait:NLS193 (control) and weargait:NLS207 (control) in the inertial records, the first two also in the force records), while the source demographic tables and the PKMAS file use the bare ids: strip the suffix before a lookup. The source PKMAS walkway file (Walkway-derived metrics/PKMAS Walkway Gait Metrics - HP+SP.csv) repeats the NLS166 SelfPace metrics in its NLS165 SelfPace row (identical rows; the NLS165 walkway contacts give 109.3 steps/min against 103.5 in that row). The source CONTROLS demographic table (CONTROLS - Demographic+Clinical - datasetV1.csv) gives the control HC134 (weargait:HC134) a height of 47 in (1.194 m) with a weight of 54 kg, a body mass index of 37.9: an adult height only in rare short-stature conditions, it may be 4 ft 7 in (1.397 m, body mass index 27.7) written without its separator. The table is kept as published; read height-based results with and without HC134. The source CSV files of the control WHC026 (weargait:WHC026, all 10 inertial records) carry its lateral shank and mid-thigh sensors under the labels of the other leg: in each of its 10 trials the angular rate of the sensors labelled L_LatShank and L_MidLatThigh is high while the left insole is loaded and the right one unloaded, the timing of a right-leg segment, and conversely for R_LatShank and R_MidLatThigh, while its ankle and dorsal-foot sensors follow their own foot, as every sensor does in 24 walking trials of 12 other controls; in its 8 trials with walking bouts the main rotation axis of each shank sensor also has the sign the other controls show on the other side. The records keep the source labels: for WHC026 read shank_L as shank_R and thigh_L as thigh_R, and conversely; the ankle, foot and insole channels are not affected.
