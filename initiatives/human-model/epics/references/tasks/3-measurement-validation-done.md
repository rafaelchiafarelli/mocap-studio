## 3. Measurement validation

- **Type:** research, with a measuring script.
- **Depends on:** `references/1`, `references/2`
- **Contract:**
  - In: Z-Anatomy's meshes for the kept structures; ANSUR II male and female CSVs,
    analyzed separately as the data's authors advise
  - Requires: each measurement's definition matched to the source's definition
  - Delivers: a table in this file: measurement, Z-Anatomy value, source value and
    spread, source, gap. Also a list of what no open source covers, starting with
    measured female anatomy
- **Pre-work:** download the ANSUR II CSVs, if `references/1` allows it
- **Out of scope:** correcting the model
- **Tests:** the measuring script's unit conversions

**Limits:** ANSUR II is external body measurement of US Army personnel, not a
civilian sample, and has no internal anatomy. Z-Anatomy comes from one male body, so a
gap may be normal variation rather than an error. Facial and muscle measurements
need other sources, to be found here.

Sources: [ANSUR II](https://www.openlab.psu.edu/ansur2/),
[Army overview](https://ph.health.mil/topics/workplacehealth/ergo/Pages/Anthropometric-Database.aspx).

## Result (2026-11-03)

Scripts: `human-model/references/measure_reference.py` (inside Blender, read-only),
`human-model/tools/ct_stats.py`, `human-model/tools/validation_table.py`. Male columns,
because Z-Anatomy is one male body. The CT sample is 130 male and 108 female scans aged
20 to 65, without recorded trauma.

| Measurement | Z-Anatomy | Source mean ± SD (male) | n | z | Source |
|---|---:|---:|---:|---:|---|
| Stature, bone to bone (skin adds about 2 cm) | 1694 mm | 1756 ± 69 mm | 4082 | -0.9 | ANSUR II `stature` |
| Biacromial breadth (scapula to scapula) | 347 mm | 416 ± 19 mm | 4082 | -3.6 | ANSUR II `biacromialbreadth` |
| Bi-iliac breadth | 270 mm | 275 ± 18 mm | 4082 | -0.3 | ANSUR II `bicristalbreadth` |
| Bizygomatic breadth (bone; skin adds about 1 cm) | 125 mm | 143 ± 6 mm | 4082 | -2.9 | ANSUR II `bizygomaticbreadth` |
| Humerus length | 320 mm | too few complete labels | 1 | — | TotalSegmentator CT |
| Bi-iliac width | 270 mm | 286 ± 23 mm | 91 | -0.7 | TotalSegmentator CT, uncut labels |
| Pelvis height | 215 mm | 225 ± 13 mm | 91 | -0.8 | TotalSegmentator CT, uncut labels |
| Sacrum width | 123 mm | 119 ± 6 mm | 121 | +0.6 | TotalSegmentator CT, uncut labels |
| Clavicle length | 160 mm | 157 ± 12 mm | 11 | +0.3 | TotalSegmentator CT, uncut labels |
| Scapula length | 191 mm | 184 ± 22 mm | 12 | +0.3 | TotalSegmentator CT, uncut labels |

**What this says:** Z-Anatomy is on the small side but inside normal variation for
stature, pelvis and sacrum. Two gaps stand out: biacromial and bizygomatic breadth, at
about 3 SD below. Part of that is definition, because ANSUR measures over skin and muscle,
and Z-Anatomy here is bone only. So they're not proof of an error. Nothing was corrected,
as the contract says. Z-Anatomy stays a comparison only (`references/1`).

**Limits of the numbers:**

- ANSUR II is US Army personnel, as this file's limits section says.
- The CT sample comes from clinical routine at the hospital sites coded in `meta.csv`, with disease
  recorded in many of them. Age and sex come from `meta.csv`.
- **Arms are almost always clipped in CT.** A first run reported a mean humerus of 128 mm,
  because the field of view cuts arms at its sides. Labels that touch any face of the volume
  or are shorter than a floor (`measures.COMPLETE_MIN`) now don't count. That floor can bias
  a mean upward, and it leaves humerus and skull with too few labels to compare.

**What no open source covers, as far as this session found:**

- **Female internal anatomy is no longer the largest gap for bones.** The CT dataset has 510
  female scans, and BMF is a female lower limb. Female forearm and hand bones still come from
  the Rajagopal model, whose geometry isn't female-specific. Muscle bodies exist only for the
  labels below.
- Muscle bodies in the CT labels: gluteus maximus, medius and minimus, iliopsoas and
  autochthon only. Their commercial task for thigh and shoulder muscles needs a paid license,
  which we don't use.
- Forearm, hand, shin and foot aren't in the CT labels at all.
- **Face muscle measurements:** no open dataset found. Face muscles are declared from
  anatomy descriptions and are the least validated part of the model.
- Hyoid and larynx: no mesh with an allowed license was found.
